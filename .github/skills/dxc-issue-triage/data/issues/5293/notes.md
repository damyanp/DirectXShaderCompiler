# Issue 5293 — Assert in `template` + `out` functions when it has local variables

**Verdict: reproduces.** Open, still present, and present in every shipped release from
v1.7.2308 (Aug 2023) to the newest catalogued v1.9.2607. Not fixed.

Triaged with `main-debug` = `1.9.0.5433 (triage, ab5400907)`, public commit `13730886e`,
a **Debug** build. Batch batch-013.

---

## 1. What the issue is

A function template with a scalar `out` parameter and at least one local variable trips an
assert in Clang's uninitialized-variables analysis when the template is instantiated:

```
tools/clang/lib/Analysis/UninitializedValues.cpp:232
ValueVector::reference CFGBlockValues::operator[](const VarDecl *vd) {
  const Optional<unsigned> &idx = declToIndex.getValueIndex(vd);
  assert(idx.hasValue());            // <-- fires
  return scratch[idx.getValue()];
}
```

`DeclToIndex::computeMap(dc)` walks the DeclContext's declarations to build the index map.
For a **function-template instantiation** the `out` ParmVarDecl is not among them, so the
lookup for the assignment `result = 10;` returns an empty `Optional`.

That single fact explains all three workarounds the description names, which is the main
reason to believe the diagnosis rather than merely the symptom:

| Workaround | Why it works |
| --- | --- |
| remove the template | the parameter is in the DeclContext, so the map has it |
| remove the local variable | `declToIndex.size() == 0`, so `hasNoDeclarations()` early-returns and the analysis never runs |
| `out` -> `inout` | `isTrackedVar()` takes the HLSL out-param path only for `HLSLOutAttr` without `HLSLInAttr` |

Each is measured as a control (`control-no-template.hlsl`, `control-no-local.hlsl`,
`control-inout.hlsl`), and each exits 0 while the repro asserts.

### The scalar-only boundary

`isTrackedVar()` tracks an HLSL `out` parameter only when `ty->isScalarType()`. Locals are
tracked more broadly (vectors and records too). So:

* `out uint` / `out float` — tracked, asserts
* `out float2` — not tracked, clean (`control-vector-out.hlsl`, exit 0)

This is not a detail. It decides whether the 2026-08-10 report reproduces as written — see
section 4.

---

## 2. Ground truth

| File | What it is | main-debug |
| --- | --- | --- |
| `repro.hlsl` | the description's example, verbatim | **0xE0000001** |
| `repro-release-crash.hlsl` | same, 32 locals instead of 1 | **0xE0000001** |
| `repro-asobo.hlsl` | the 2026-08-10 `TRayVsAABB` as quoted | 0x00000000 |
| `repro-asobo-scalar-out.hlsl` | that function plus a scalar `out T` | **0xE0000001** |
| `control-no-template.hlsl` | workaround 1 | 0x00000000 |
| `control-no-local.hlsl` | workaround 2 | 0x00000000 |
| `control-inout.hlsl` | workaround 3 | 0x00000000 |
| `control-vector-out.hlsl` | `out float2` | 0x00000000 |
| `control-caller-initialised.hlsl` | caller's variable initialised | **0xE0000001** |
| `control-release-crash-no-template.hlsl` | 32 locals, no template | 0x00000000 |
| `control-release-crash-inout.hlsl` | 32 locals, `inout` | 0x00000000 |

`0xE0000001` is `STATUS_LLVM_ASSERT`; stderr carries `Internal compiler error: LLVM Assert`.

`control-caller-initialised.hlsl` matters as an identity control: writing `uint x = 0;` at
the call site changes nothing, because the failure is in the analysis of the *instantiated
callee*, not of the caller. It rules out "the caller's variable is uninitialised" as the
story.

Stack, captured under `cdb`, in `manual-case-assert-stack.txt`:

```
CFGBlockValues::operator[]            UninitializedValues.cpp:232
TransferFunctions::VisitBinaryOperator
runUninitializedVariablesAnalysis
AnalysisBasedWarnings::IssueWarnings
Sema::ActOnFinishFunctionBody
Sema::InstantiateFunctionDefinition    <-- instantiation, as diagnosed
```

---

## 3. The Release/Debug split, and why a naive bisect says "fixed"

Every catalogued release is a **Release** build, so the assert is compiled out. `repro.hlsl`
therefore exits **0** on all 20 of them. `bisect --linear --repeat 5` duly returned
`never-repro'd across v1.4.1907..v1.9.2607`.

That result is not evidence of a fix, and taking it at face value would have produced a
wrong verdict. The tool said so itself, warning that `0xE0000001` is assert-only.

What actually happens with `NDEBUG` is what simontaylor81 (Frostbite) predicted in the
2024-05-20 comment: the valueless `Optional` is read anyway and the garbage index is used to
subscript `scratch`. Continuing past the assert under `cdb` (`manual-case-ndebug-path.txt`)
shows the cascade:

```
Optional::getValue        assert(hasVal)
Optional::getPointer
SmallBitVector::operator[]  "Out-of-bounds Bit access."
SmallBitVector::set         "undefined behavior"
```

His reasoning was right, and the following makes it measurable.

### Making a Release build crash

`scratch` is `PackedVector<Value, 2, SmallBitVector>`. `SmallBitVector` stores bits inline
while they fit in `SmallNumDataBits = 57` (`include/llvm/ADT/SmallBitVector.h`), i.e. 28
two-bit entries; past that it heap-allocates and the out-of-bounds index stops being a
masked shift and becomes a wild pointer access.

Measured on the shipped **v1.9.2607 Release** binary, varying only the number of locals:

| locals | exit |
| --- | --- |
| 27 | 0x00000000 |
| 28 | 0x00000000 |
| **29** | **0xC0000005** |
| 30, 32, 40, 64, 120 | 0xC0000005 |

The flip is exactly at the predicted boundary. `repro-release-crash.hlsl` uses 32.

Scored by the triage tool against the same predicate, on that release binary:

```
repro-release-crash.hlsl                  exit=0xC0000005  -> repro
control-release-crash-no-template.hlsl    exit=0x00000000  -> no-repro
control-release-crash-inout.hlsl          exit=0x00000000  -> no-repro
repro.hlsl                                exit=0x00000000  -> no-repro
```

The last two lines are the whole point: **the same binary, same defect — one shader exits 0
and another access-violates.** "Exits 0" was never a fix, only a small enough input.

---

## 4. Does the 2026-08-10 report reproduce?

Yes as a class; no as literally quoted, and the difference is useful to the reporter.

`TRayVsAABB` as posted has `out T2 intersections` where `T2` is a 2-vector (it is built as
`T2(tClose, tFar)`). A vector `out` is not tracked by `isTrackedVar`, so the function as
quoted compiles cleanly here — exit 0, `repro-asobo.hlsl`. Adding one scalar `out T` to that
same function makes it assert immediately (`repro-asobo-scalar-out.hlsl`, 0xE0000001).

So the trigger in that codebase is a **scalar** `out` in a template, most likely in a
different function than the one quoted.

### "It was not crashing before"

Two independent explanations, both supported:

1. **A DXC upgrade across v1.7.2212.1 -> v1.7.2308.** No release at or below v1.7.2212.1
   crashes; every release from v1.7.2308 on does. See the matrix below.
2. **No DXC change at all.** Because the small/large flip is at 29 tracked locals, adding a
   few locals to an existing templated function moves it from silently-wrong to hard crash
   with no compiler change whatsoever. This is worth flagging: the bug is latent long before
   it is visible.

Note that the pre-v1.7.2308 releases are not "correct" — they simply lack the analysis that
contains the defect, so nothing looks at the `out` parameter at all.

---

## 5. Release history

`measure-releases.py` regenerates `manual-case-release-matrix.txt` (every command echoed).

```
build           HV2021  WPARAM  repro       asobo-scalar-out  release-crash  rc-no-tmpl  rc-inout
main-debug      yes     yes     0xE0000001  0xE0000001        0xE0000001     0x00000000  0x00000000
v1.4.1907       no      no      0x00000001  0x00000001        0x00000001     0x00000001  0x00000001
v1.5.2010       no      no      0x00000001  0x00000001        0x00000001     0x00000001  0x00000001
v1.6.2104       no      no      0x00000001  0x00000001        0x00000001     0x00000001  0x00000001
v1.6.2106       no      no      0x00000001  0x00000001        0x00000001     0x00000001  0x00000001
v1.6.2112       yes     no      0x00000000  0x00000000        0x00000000     0x00000000  0x00000000
v1.7.2207       yes     no      0x00000000  0x00000000        0x00000000     0x00000000  0x00000000
v1.7.2212       yes     no      0x00000000  0x00000000        0x00000000     0x00000000  0x00000000
v1.7.2212.1     yes     no      0x00000000  0x00000000        0x00000000     0x00000000  0x00000000
v1.7.2308       yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.8.2403       yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.8.2403.1     yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.8.2403.2     yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.8.2405       yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.8.2407       yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.8.2502       yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.8.2505       yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.8.2505.1     yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.9.2602       yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.9.2602.24    yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
v1.9.2607       yes     yes     0x00000000  0x00000000        0xC0000005     0x00000000  0x00000000
```

Reading the columns:

* **HV2021** — `-HV 2021` accepted at all. The four oldest releases reject it
  (`dxc failed : Unknown HLSL version: 2021`, exit 1). Their `0x00000001` is an **invalid
  probe**, not a negative: they never compiled the file. See `method-notes.md`.
* **WPARAM** — whether `-Wparameter-usage` is emitted, i.e. whether the uninitialized
  out-parameter analysis exists at all (`control-outparam-presence.hlsl`). Absent up to
  v1.7.2212.1, present from v1.7.2308.
* **WPARAM predicts release-crash exactly**: `no` -> 0x0, `yes` -> 0xC0000005, with no
  exceptions across 17 valid probes. Two independently derived signals agreeing on the same
  boundary is the strongest single piece of evidence in this triage.

So only **12** of 20 releases are valid evidence of the defect's presence, and all 12 crash.
Four cannot compile the repro; four more predate the code under test.

### Dating it in the tree

```
git log --all -S 'hlslOutParams' --oneline
  1380cf88e  2023-03-01  Chris B  Add diagnostics for uninitialized `out` parameters (#5047)
```

`git merge-base --is-ancestor 1380cf88e <tag>`: absent from v1.7.2212.1 and earlier, present
from v1.7.2308. This matches the behavioural boundary exactly, from a different direction.

---

## 6. Compiler Explorer

<https://godbolt.org/z/MKsnrdq4T> — verified, HTTP 200; full pane output in
`manual-case-godbolt-verify.txt`, rationale in `godbolt-note.txt`.

```
dxc 1.7.2212   exit 0     last release before the analysis existed
dxc 1.7.2308   SIGSEGV    first release containing 1380cf88e
dxc trunk      SIGSEGV    still present
```

The link publishes `repro-release-crash.hlsl`, not `repro.hlsl`, precisely because CE runs
Release builds and `repro.hlsl` exits 0 on all of them.

CE **corroborates and does not overrule** the local Debug build: it reproduces the boundary
on Linux, with a different toolchain, on infrastructure nobody here controls. It cannot show
the assert, having no Debug DXC.

---

## 7. Existing fix attempt

PR **8401**, "Add defensive checks for declToIndex entries", branch `issue-5293`, by
tcorringham — **open and not merged** as of 2026-08-10 (last updated 2026-08-05). It names
this issue and 8310 in its body and includes a release-note entry.

So a fix is in flight but has not landed, which is consistent with everything measured here.
No comment on its approach or timeline.

---

## 8. Standing statements this evidence contradicts

The 2023-06-23 maintainer comment says the assert "does not result in any impact on AST
formation or code generation" and that LLVM "still expects the code to behave correctly if
the assert is removed".

For this instance that is not what happens. With the assert removed the code reads a
valueless `Optional` and subscripts a bit vector out of bounds — measured, in
`manual-case-ndebug-path.txt` — and past 28 locals that is a hard crash in shipping
binaries, measured on 12 consecutive releases and reproduced on Compiler Explorer.
simontaylor81 made exactly this argument in 2024 and it was never resolved on the thread.

The verdict is recorded with `--text-stale` for this reason.

---

## 9. Labels

Currently only `bug`. Checked against the live taxonomy (`triage.py labels --refresh`,
58 labels), reading descriptions rather than names:

| Label | Description | Why |
| --- | --- | --- |
| `crash` | "DXC crashing or hitting an assert" | Both manifestations, verbatim. The clearest gap: `bug` alone hides that this is a crash. |
| `hlsl2021` | "Pertaining to HLSL2021 features" | The construct is a function template; requires `-HV 2021`, and no release without HLSL 2021 can even express it. |
| `diagnostic` | "Issues for diagnostics" | The defect is *in* the uninitialized-out-parameter diagnostic added by 1380cf88e, not in codegen. |
| `high-impact` | "For high impact usability issues" | Optional, maintainer judgement. Two studios blocked, 12 shipping releases affected, and it corrupts memory rather than failing cleanly. Workarounds exist (`inout`, drop the template), which is why this is offered rather than argued. |

Explicitly **not** proposed: `validation` (means DXIL validation/signing — unrelated),
`needs repro steps` (repros are attached), `correctness` (the primary symptom is a crash,
though the wrong-attribution point in section 8 is adjacent).
