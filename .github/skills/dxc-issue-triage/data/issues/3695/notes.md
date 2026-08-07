# #3695 — DXC Crash on Bad Shader

**Status: `repros`.** Reported 2021-04-19; still reproduces on `main` and on every release
binary back to the bisection floor.

## Ground truth

| | |
| --- | --- |
| compiler id | `main-debug` |
| `dxc --version` | `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` |
| commit | `ab5400907` |
| provenance check | `git diff --name-only ab5400907 HEAD` touches nothing outside `.github/skills/dxc-issue-triage/`, so no compiler source differs from `HEAD` (`111ac3828`). Checked by tree/diff rather than by SHA, per SKILL.md. |

## Repro

`repro.hlsl` is a **byte-for-byte copy** of the issue's own attachment
(`attachment-shader.txt`, SHA-256 `2A4787553E150F6B119C40AF0026ED50B6B0350F15904651CFBE0B7D5E614CDF`,
fetched from `files/6338441/shader.txt`), which is also what pow2clk pasted inline in the
first comment. `cmd.txt` is `-T cs_6_0 -E main repro.hlsl`; `cmd-as-filed.txt` records the
three cosmetic departures from `dxc /Tcs_6_0 /Emain shader.txt` (flag spelling, spacing,
filename) and why. **Repro quality: `complete`.** No workaround flags were filed, so there
was none to question.

Two configuration questions from `expected.md`, both settled by measurement rather than
assumption:

- the `.txt` extension is irrelevant — `variant-as-filed-txt-main-debug.txt` runs the
  original file under its original name and crashes identically;
- damyanp's 2024 Compiler Explorer link uses `-T cs_6_6`, not the body's `cs_6_0`.
  `variant-cs66-main-debug.txt` crashes identically, so the profile is not load-bearing. The
  body's `cs_6_0` is what `cmd.txt` uses.

## Predicate

`match.json` is `internal_failure`. The choice matters in both directions here and the note in
the file spells it out:

- the shader **is invalid**, so the correct behaviour is a diagnostic, and dxc returns E_FAIL
  (0x80004005) for those. A `nonzero_exit` predicate would have scored a correctly-diagnosing
  compiler as reproducing the crash;
- the crash's *shape* changes across builds. Debug `main` raises the assert as a C++ exception
  (0xE0000001); all 20 release binaries access-violate (0xC0000005); and **two of them print
  nothing at all**. A predicate keyed to any message text would have invented a fix boundary.

`match-accepts.json` (`nonzero_exit` inverted, i.e. "exited 0") exists for the body's other
claim — *"shouldn't compile successfully"*. On `main` it scores **`invalid-probe`**, correctly:
a build that crashed never answered the question of whether it would have accepted the shader.
No build in this triage exited 0 on the repro, so nothing was ever silently accepted; the whole
history is crashes. The second predicate was therefore not bisected — 20 identical
`invalid-probe` rows would add filenames, not evidence.

### Controls

| capture | shader | expect | result |
| --- | --- | --- | --- |
| `variant-control-valid-main-debug.txt` | `control-valid.hlsl` | `no-match` | exit 0, full DXIL. The predicate does not fire on a known-good input |
| `variant-as-filed-txt-main-debug.txt` | `attachment-shader.txt` | `match` | identity control: the original file under its original name |
| `variant-cs66-main-debug.txt` | repro at `-T cs_6_6` | `match` | damyanp's CE configuration |
| `variant-minimal-crash-main-debug.txt` | `minimal-crash.hlsl` | `match` | minimised form, Debug `main` |
| `variant-minimal-crash-v1.9.2607.txt` | `minimal-crash.hlsl` | `match` | minimised form, newest release |
| `variant-minimal-assign-main-debug.txt` | `minimal-assign.hlsl` | `no-match` | **diagnosed, not a crash** |
| `variant-minimal-return-main-debug.txt` | `minimal-return.hlsl` | `no-match` | **diagnosed, not a crash** |

`control-valid.hlsl` differs from the repro in exactly the three invalid constructs and
nothing else — same root signature, same globals, same loops, same `GetDimensions`.

Both `minimal-*` files were first declared `--expect match` on a hypothesis that turned out to
be wrong; `run` warned, and the declaration was corrected with `triage.py expect` (which
refuses a declaration that would itself be false). The measurements were not touched.

## What the compiler does

`main`, Debug (`out-main-debug.txt`, exit `0xE0000001`):

```
Internal compiler error: LLVM Assert
```

That is the whole output. No diagnostic, no source location — exactly what the body describes.
Under `cdb` (`manual-case-assert-stack.txt`):

```
Error: assert(Val && "isa<> used on a null pointer")
File:
<repo>/include/llvm/Support/Casting.h(96)
Func:   llvm::isa_impl_cl<class llvm::CallInst,class llvm::Instruction const *>::doit
```

with the frames below it:

```
07 dxcompiler!hlsl::OP::IsDxilOpFuncCallInst
09 dxcompiler!hlsl::DxilInst_CreateHandleForLib::operator bool
0a dxcompiler!`anonymous namespace'::DxilLowerCreateHandleForLib::ReplaceResourceUserWithHandle+0xd7
0b dxcompiler!`anonymous namespace'::DxilLowerCreateHandleForLib::TranslateDxilResourceUses+0xa00
0c dxcompiler!`anonymous namespace'::DxilLowerCreateHandleForLib::GenerateDxilResourceHandles+0x1ce
0d dxcompiler!`anonymous namespace'::DxilLowerCreateHandleForLib::runOnModule+0x50d
```

**This is not an `NDEBUG` artefact.** Two independent lines of evidence:

1. `gh`-ing past the assert in the debugger — which emulates the code path a build with the
   assert compiled out would take — lands on an **access violation** in
   `llvm::Value::getValueID`, from the same `ReplaceResourceUserWithHandle` frame
   (second case in `manual-case-assert-stack.txt`).
2. All 20 release binaries, which are Release/`NDEBUG` builds, do access-violate.

Source corroboration (`lib/HLSL/DxilCondenseResources.cpp:2040-2049`) matches the frames:

```cpp
CallInst *CI = dyn_cast<CallInst>(V);
DxilInst_CreateHandleForLib createHandle(CI);
DXASSERT(createHandle, "must be createHandle");
CI->replaceAllUsesWith(handle);
```

`dyn_cast` yields null for a user that is not a `CallInst`; evaluating `createHandle` for the
`DXASSERT` calls `IsDxilOpFuncCallInst(nullptr)`, which is the assert. With the assert compiled
out the next line dereferences the same null. This is offered as corroboration of the captured
stack, not as a diagnosis of *why* a non-call user reaches that loop.

## History

`bisect --linear`, 20 releases, **all `repro`, no invalid probes**:

```
v1.4.1907 v1.5.2010 v1.6.2104 v1.6.2106 v1.6.2112 v1.7.2207 v1.7.2212 v1.7.2212.1
v1.7.2308 v1.8.2403 v1.8.2403.1 v1.8.2403.2 v1.8.2405 v1.8.2407 v1.8.2502 v1.8.2505
v1.8.2505.1 v1.9.2602 v1.9.2602.24 v1.9.2607        -> always-repro'd
```

Every one exits `0xC0000005`. Eighteen print
`Internal compiler error: access violation. Attempted to read from address 0x0000000000000019`;
**v1.4.1907 and v1.5.2010 print nothing at all** — empty stdout *and* empty stderr, exit
0xC0000005. Recorded here because it is the exact failure mode a text-based crash predicate
would have missed.

`--linear` rather than plain bisection: the endpoints agree, so a binary search would have
short-circuited after two probes and the claim would have covered two releases, not twenty.
`--repeat` was not used and was not needed — the crash is deterministic, every probe scored
`repro`, and there is no clean result anywhere in the scan that could have been an unlucky run.

The report is dated 2021-04-19. v1.4.1907 (2019-07) and v1.5.2010 (2020-10) both predate it and
both crash, so the history covers the issue's entire life. The catalog's `v1.5.2003` hole is not
relevant to a 2021 issue and was not probed; the releases either side of the report date
(v1.5.2010, v1.6.2104) are both in the scan and both crash.

## Minimisation

`manual-case-minimisation.txt` walks eight candidates. The result corrects a detail of the
issue body, which says the crash *"[s]eems to be related to assigning one `RWTexture2D<float4>`
global variable to another"*:

| | construct | exit |
| --- | --- | --- |
| C1 | `A = B;` — one global to another | `0x80004005`, **diagnosed** |
| C2 | `local = pick(B); A = local;` — via a resource-returning function, different global | `0x80004005`, **diagnosed** |
| C3 | `local = pick(A); A = local;` — via the function, back into the **same** global | `0xE0000001` **crash** |
| C4–C8 | C3 plus `GetDimensions`, plus stores, plus a loop | `0xE0000001` **crash** |

Both diagnosed cases emit
`error: local resource not guaranteed to map to unique global resource.` So the assignment
alone is handled; what crashes is the round trip through a function back into the same global.
C3 is committed as `minimal-crash.hlsl` (10 lines), and it crashes Debug `main`, release
v1.9.2607 locally, and both CE DXC panes.

I did **not** set `text_stale`. The body's load-bearing claims — invalid shader, crashes, no
error message, plus a repro that still works — are all exactly right, and the sentence above is
explicitly hedged ("Seems to be related to"). SKILL.md's bar for `text_stale` is that the text
*misdescribes what the compiler does* such that a reader spot-checking it concludes "cannot
reproduce"; here the attached repro reproduces on the first try. The refinement belongs in the
comment, which is where it is.

## Compiler Explorer

<https://godbolt.org/z/aqPedMGE4> — verified by reading back
`GET /api/shortlinkinfo/aqPedMGE4`: three panes (`dxc_1_6_2112`, `dxc_trunk`,
`hlsl_clang_trunk`), all at `-T cs_6_0 -E main`, carrying the banner plus the repro.

Full pane text is in `manual-case-godbolt-verify.txt`:

- both DXC panes: `Program terminated with signal: SIGSEGV`, exit 139;
- `hlsl_clang_trunk`: **exit 1 with a specific diagnostic**, 30-odd lines past the pane's
  first line —

  ```
  <source>:84:14: error: assignment to global resource variable '_blurResult' is not allowed
     84 |         _blurResult = filterFog;
  <source>:35:21: note: variable '_blurResult' is declared here
  ```

CE runs Linux **Release** builds, so it cannot show the assert; it corroborates the local Debug
build and does not overrule it.

### Clang controls

Per SKILL.md a Clang error is not evidence without a control, and here the control initially
*failed*: `control-valid.hlsl` on `hlsl_clang_trunk` at the repro's own flags dies with
`fatal error: error in backend: DXIL Store not implemented for texture resources`. Clang's DXIL
backend cannot lower a texture store yet, so it cannot validate a Clang *backend* result. The
control was therefore repeated with `-fsyntax-only`, and both halves are in
`manual-case-ce-controls.txt`:

| shader | args | exit |
| --- | --- | --- |
| `control-valid.hlsl` | `-fsyntax-only` | **0** (warnings only) |
| `repro.hlsl` | `-fsyntax-only` | 1, the same `assignment to global resource variable` error |
| `control-valid.hlsl` | plain, `dxc_trunk` | 0, full DXIL |
| `minimal-crash.hlsl` | plain, `dxc_trunk` / `dxc_1_6_2112` | 139 / 139 |
| `minimal-crash.hlsl` | plain, `hlsl_clang_trunk` | 1, diagnosed |
| `minimal-assign.hlsl` | plain, `dxc_trunk` | 5, diagnosed (Linux dxc's error status) |

So Clang's diagnostic comes from Sema, before the backend gap, and a known-good input passes
the same front end cleanly. The **published** pane needs no `-fsyntax-only`: the Sema error is
fatal, so the backend never runs and the pane is already clean.

## Labels

Now: `bug`, `crash`, `incorrect-code` — all three are supported by the evidence and none should
be removed.

Proposed addition: **`diagnostic`** ("Issues for diagnostics"). The whole issue is that invalid
code produces no diagnostic. The combination is established repo practice, not an invention —
`manual-case-label-precedent.txt` captures the query: four issues already carry all four of
`bug,crash,diagnostic,incorrect-code`, and the closest in shape is **#5681 "Segmentation
fault/ICE when attempting a particular (invalid) code pattern"**, alongside #7582, #6964 and
#6016. `diagnostic` is live, not vestigial: 56 issues carry it, 35 of them open.

`check-in-clang` ("See if this repros in clang as well") was considered and **rejected**: it
requests a check that this triage has already performed, and the answer — Clang diagnoses it —
is in the draft comment and in `manual-case-ce-controls.txt`. Labelling it would ask for work
that is done. Noted here so the decision can be second-guessed at collation.

## Assessment

| | |
| --- | --- |
| status | `repros` |
| repro quality | `complete` |
| history | `always-repro'd` across v1.4.1907..v1.9.2607 (all 20 releases, linear) |
| confidence | high |
| suggested action | `still-valid-keep-open` |
| text stale | no (see reasoning above) |

Deterministic, reproduces on every build that can be tested, in the issue's own repro and in a
10-line minimisation, on two profiles, on Windows and on CE's Linux builds. There is nothing
ambiguous to weigh.

## Cross-reference check

`gh api repos/microsoft/DirectXShaderCompiler/issues/3695/timeline` lists **no**
cross-referenced events at all, before or after this triage.
