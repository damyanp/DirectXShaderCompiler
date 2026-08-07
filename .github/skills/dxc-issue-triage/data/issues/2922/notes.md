# #2922 — value-to-declare pass not handling pointer case under -O1

**Verdict: does not reproduce. Fixed between v1.6.2112 and v1.7.2207, by
`c0676c7ca` (PR #4375, Adam Yang, 2022-04-05).**

Ground truth: `build\Debug\bin\dxc.exe`, `dxcompiler.dll 1.10(5433-ab540090)(1.9.0.5433)`,
`main` @ `ab5400907`.

---

## 1. What the issue asks for

The body, in full:

> Repro: e.g., open PixTest.cpp, find the "Compile" function and change the -Od to -O1, then
> run the taef tests with `/name:PixTest::PixStructAnnotation_*`

Filed 2020-05-27 by `jeffnn` (a DXC/PIX maintainer). No labels. One comment, from `damyanp`
on 2024-06-27 — *"@jeffnn - is this something we still need to track?"* — never answered.
The measured answer to that question is **no**: it had already been fixed two years before it
was asked.

`value-to-declare` is `DxilDbgValueToDbgDeclare`
(`lib/DxilPIXPasses/DxilDbgValueToDbgDeclare.cpp`, option `-dxil-dbg-value-to-dbg-declare`).
It converts `llvm.dbg.value` records into `llvm.dbg.declare` plus stores into synthetic
allocas, which is how PIX's shader debugger recovers local variables. At `-Od` dxc emits
`llvm.dbg.declare` directly, so the pass has nothing to do. At `-O1` it emits
`llvm.dbg.value` whose value operand is a **pointer** to the local's alloca — and
`handleDbgValue` used to bail out unconditionally on that:

```c++
  if (auto *PtrTy = llvm::dyn_cast<llvm::PointerType>(V->getType())) {
    VALUE_TO_DECLARE_LOG("... variable had null pointer type");
    return;
  }
```

The variable was dropped, and PIX lost it.

## 2. Why this issue needed a harness rather than a `cmd.txt`

The symptom is not visible from `dxc.exe`. `-dxil-dbg-value-to-dbg-declare` is a PIX pass
exposed only through `IDxcOptimizer`; `dxc.exe` never runs it, and the fix changed *only*
that pass, so **dxc's own output is identical on both sides of the fix**. No predicate over
dxc's stdout can distinguish them. Two things follow, and both are recorded loudly in
`match.json` and in the verdict's `history`:

* `cmd.txt` covers the **compile half only** — it establishes the precondition (that `-O1`
  really hands the pass a pointer-typed `dbg.value`), nothing more.
* **`bisect`'s answer for this issue is not the symptom history.** It reported
  `regressed-in v1.6.2104 (last good: v1.5.2010)`. That is the release where dxc first emitted
  `DILocalVariable`/`llvm.dbg.value` for this shader at all — the precondition appearing, not
  the bug appearing. Reading it as a regression point would be wrong in both direction and date.

`measure.py` does the real measurement. For each build and each of `-Od`/`-O1`:

```
<dxc.exe>   -T as_6_5 -E main /Zi /Qembed_debug -HV 2018 -enable-16bit-types <-Od|-O1> repro.hlsl
<dxopt.exe> -external <THAT BUILD's dxcompiler.dll> -external-fn DxcCreateInstance \
            -o=<bc> <ll> -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
<opt.exe>   -S <bc>
```

`dxopt -external` is the key: it makes the *release's own* `dxcompiler.dll` supply
`IDxcOptimizer`, so each row measures that release's pass. `dxopt.exe`/`opt.exe` come from the
local build and are only plumbing (blob marshalling, disassembly) — release packages ship
neither.

The compile arguments are exactly PixTest's: `TestStructAnnotationCase` in `PixTest.cpp` uses
`as_6_5`, `-HV 2018`, `-enable-16bit-types`; `Compile` in `PixTestUtils.cpp` prepends
`/Zi /Qembed_debug`. The pass list is exactly `RunAnnotationPasses`'.

`repro.hlsl` is `PixStructAnnotation_FloatN`'s shader verbatim — one of the three tests whose
`-O1` half was disabled *for this bug*.

## 3. The observable, and a discriminator that would have lied

The observable is the number of `call void @llvm.dbg.declare` **instructions in the pass
output**. That is the pass's entire product, and `PixTest` builds the `AllocaWrites` it
asserts on by walking exactly those `DbgDeclareInst`s. Zero of them at `-O1`, on a module that
does contain a pointer-typed `dbg.value`, is the reported defect.

The obvious alternative — "does the output carry `!pix-alloca-reg-write` metadata?" — is
**wrong, and would have reported the bug as absent**. The broken `-O1` output has two such
tags, on the stores into the shader's own `%p1` alloca. So does the healthy `-Od` control.
Only the post-fix `-O1` output has four. Presence is not a discriminator; the count is, but it
is 2 for both the defect and the control. See `method-notes.md`.

## 4. Results

`manual-case-release-history.txt` (produced by `python measure.py --history`), 21 builds:

| build | `-O1` ptr `dbg.value` in | `dbg.declare` out | verdict |
| --- | --- | --- | --- |
| v1.4.1907 | — | — | invalid-probe: `error: invalid profile as_6_5` |
| v1.5.2010 | 0 | 0 | invalid-probe: emits no `DILocalVariable` at all |
| v1.6.2104 | 1 | **0** | **repro** |
| v1.6.2106 | 1 | **0** | **repro** |
| v1.6.2112 | 1 | **0** | **repro** |
| v1.7.2207 … v1.9.2607 (15 releases) | 1 | 2 | no-repro |
| main-debug (`ab5400907`) | 1 | 2 | **no-repro** |

Both invalid probes are resolved by their own `-Od` control row rather than assumed:
v1.4.1907 rejects the profile outright, and v1.5.2010 produces no `llvm.dbg.*` record for the
local at `-Od` either — it emits a line table and a `DISubprogram` but no `DILocalVariable` —
so the pass has no input on that release and its behaviour is not evidence about #2922 either
way. This is exactly the `invalid-probe` trap: a build that never reaches the code under test
looks identical to a build that is clean.

`@main` after the pass, verbatim (full bodies in `manual-case-release-history.txt`):

**v1.6.2112, `-O1`** — no `llvm.dbg` record survives; the variable is gone:

```llvm
define void @main() {
  %p1 = alloca %struct.smallPayload.0, align 8, !pix-dxil-inst-num !38, !pix-alloca-reg !39
  ...
  call void @dx.op.dispatchMesh.struct.smallPayload.0(i32 173, i32 1, i32 1, i32 1, %struct.smallPayload.0* nonnull %p1), ...
  ret void, ...
}
=> llvm.dbg.declare instructions in @main: 0
```

**main @ `ab5400907`, `-O1`** — one declare per component, on synthesised debug registers:

```llvm
  %0 = alloca [1 x float], i32 0, !pix-alloca-reg !37
  call void @llvm.dbg.declare(metadata [1 x float]* %0, metadata !38, metadata !42), !dbg !43 ; var:"p" !DIExpression(DW_OP_bit_piece, 0, 32)
  %1 = alloca [1 x float], i32 0, !pix-alloca-reg !36
  call void @llvm.dbg.declare(metadata [1 x float]* %1, metadata !38, metadata !44), !dbg !43 ; var:"p" !DIExpression(DW_OP_bit_piece, 32, 32)
  ...
  %4 = load %struct.smallPayload.0, %struct.smallPayload.0* %p1, !dbg !54, ...
=> llvm.dbg.declare instructions in @main: 2
```

That `load` is literally the `B.CreateLoad(V)` the fix introduced — the fix is not merely
present, it is observably executing.

### The reporter's own repro, run as written

`manual-case-taef.txt` / `manual-case-taef-raw.txt`:

```
$ TE.exe ClangHLSLTests.dll /name:PixTest::PixStructAnnotation_*
Summary: Total=18, Passed=18, Failed=0, Blocked=0, Not Run=0, Skipped=0
```

The instruction "change the -Od to -O1" can no longer be followed, because that edit is
already upstream. `PixTest.cpp` now runs every case at both levels:

```c++
static const OptimizationChoice OptimizationChoices[] = {
    {L"-Od", false},
    {L"-O1", true},
};
```

and the three per-test opt-outs are gone — the same commit deleted all three occurrences of

```c++
break; // don't run -O1 test until pointer types are dealt with by value-to-declare pass
```

from `PixStructAnnotation_FloatN`, `_SequentialFloatN` and `_EmbeddedFloatN`. Those opt-outs
were themselves added *after* this issue was filed — `265492784` (#3289, 2020-12-01), six
months later — so their whole lifetime, 2020-12-01 to 2022-04-05, is the period during which
the test suite was deliberately not testing what this issue reports. So "run the taef tests"
*is* the `-O1` test today, and it passes.

A green test suite on its own would be weak evidence — tests and fix landed together, so it
only says current behaviour matches current expectations. The pass-level measurement in §4 is
what makes it conclusive, and it was chosen for that reason before anything was run
(`expected.md`).

## 5. Attribution, and the size of the window

`manual-case-source-evidence.txt`:

```
git merge-base --is-ancestor c0676c7ca v1.6.2112  ->  NO, predates the fix
git merge-base --is-ancestor c0676c7ca v1.7.2207  ->  YES, contains the fix
```

The measured transition window `v1.6.2112 (2021-12-08) → v1.7.2207 (2022-07-18)` holds **248
commits**, of which **three** touch `DxilDbgValueToDbgDeclare.cpp`:

* `b71cfcb07` PIX: ensure allocas generated by value-to-declare dominate uses (#4145)
* `7f7278b4e` PIX: avoid crash on enumerated types without int base type (#4254)
* `c0676c7ca` **Handling dbg.value pointer case in O1. (#4375)**

Attribution to `c0676c7ca` is **strong, not certain** — I did not build at that commit. It is
supported by four independent things: the title and PR description name this exact case; the
diff deletes the unconditional pointer early-return and replaces it with the alloca-load path;
the same commit removes the three `don't run -O1 test` opt-outs from the tests this issue
names; and the `load` that fix inserts is present in main's measured pass output and absent
from v1.6.2112's.

## 6. Compiler Explorer

<https://godbolt.org/z/End684Ycq> — three panes, verified pane-by-pane through the CE API in
`manual-case-godbolt-panes.txt`.

It shows the **precondition only**, and `godbolt-note.txt` says so in the banner. Panes 1
(DXC 1.6.2112, `-O1`) and 2 (DXC trunk, `-O1`) agree — same instruction, same operand types,
differing only in metadata node numbering:

```llvm
call void @llvm.dbg.value(metadata %struct.smallPayload.0* %p1, i64 0, metadata !38, metadata !42), !dbg !43 ; var:"p"
```

Pane 3 (trunk, `-Od`) shows what the pass gets instead when the bug is dodged:

```llvm
call void @llvm.dbg.declare(metadata %struct.smallPayload.0* %p1, metadata !37, metadata !41), !dbg !42 ; var:"p"
```

CE cannot run PIX passes, so no link can show this bug present or absent. Kept anyway because
it makes the pointer operand — the whole subject of the issue title — visible in one click.
No FXC pane (no SM6, no amplification shaders). No Clang pane (DXC-only PIX pass).

## 7. Labels

Currently **none**. Proposed additions:

* `PIX` — "Issues related to PIX passes". Exact fit; this is the routing label that would have
  made the issue findable.
* `bug` — "Bug, regression, crash".
* `debug info` — "Related to debug info generation". The pass's whole product is debug records.

Not `validation` (that means DXIL validation), not `crash` (nothing crashed at any point), not
`correctness` ("bugs that impact shader correctness" — emitted DXIL was always correct; only
PIX's view of locals was lost), not `test`.

## 8. Blind reproducibility check

Required for `close-fixed`. A fresh agent on a different model (`gpt-5.6-sol`) was given this
directory with `notes.md`, `verdict.json`, `comment.md` and `method-notes.md` withheld, and
asked to state the verdict independently.

It returned the same five fields — `does-not-repro`; fixed between v1.6.2112 and v1.7.2207;
`prose-only`; `close-fixed`; `high` — and independently rejected v1.4.1907 and v1.5.2010 as
invalid evidence for the right reasons, including that `v1.5.2010 → v1.6.2104` is not a
regression. It named the same top hazard I had: the `out-*.txt` capture headers read
`no-repro` on v1.5.2010 and `repro` on main, which inverted is the wrong history.

It also found **three real defects**, all now corrected:

1. `match.json`'s note said the fix commit "touched `lib/DxilPIXPasses` only". It touched four
   files. Corrected to name them; the material point (nothing in dxc's DXIL-producing path)
   survives.
2. `godbolt-note.txt` claimed panes 1 and 2 were "identical". Their metadata node numbers
   differ. Reworded to "agree", and the link republished
   (`Mc4cT5PGr` → `End684Ycq`), panes re-verified.
3. `manual-case-source-evidence.txt` echoed a `$ git tag --contains … | sort -V` line that was
   not the command actually run — the list was `git tag`'s lexicographic order, with `v1.10`
   above `v1.7`. Regenerated so every echoed command is the one that produced the output below
   it.

None changed the verdict. All three were claims that were unsupported rather than wrong, which
is the class of error this check exists to catch.

## 9. Assessment

* **status** `does-not-repro`
* **repro quality** `prose-only` — precise, executable prose naming an in-tree test, but no
  code. `repro.hlsl`, `cmd.txt` and `measure.py` are agent-constructed from `PixTest.cpp`.
* **history** fixed between v1.6.2112 and v1.7.2207
* **confidence** `high`
* **suggested action** `close-fixed`
* **text-stale** yes — the repro instruction cannot be followed as written any more

Nothing here is a judgement about whether PIX's *current* handling is complete. The pass still
early-returns when a pointer-typed `dbg.value` is not an `AllocaInst` (`// We only know how to
handle AllocaInsts for now`), so other pointer shapes may still be unhandled. That is a
different question from the one this issue asks, and I did not test it.
