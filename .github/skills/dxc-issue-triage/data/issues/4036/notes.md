# #4036 — Odd compilation error with ResourceDescriptorHeap and type deduction

Filed 2021-10-25 by `Jasper-Bekkers`. Unlabelled; milestone **Dormant** since
2024-04-22. One comment (2021-11-08, `pow2clk`): the supported spelling is to
assign the subscript to a local, and the reported spelling *should* work, but it
is low priority because a workaround exists.

## Verdict

**changed-behavior.** The input still fails to compile on every DXC that can
run it, but it no longer fails the way the issue describes. Since **v1.7.2207**
DXC does not diagnose it at all — it aborts with an internal compiler error.

## What was tested

```
$ dxc -T ps_6_6 -E PSMain repro.hlsl
```

`repro.hlsl` is a byte-faithful reconstruction: the reporter quoted a diagnostic
pointing at line 8, column 79, and the reconstruction's line 8 column 79 is the
same character (single-tab indentation). `repro-quality: complete`.

The reporter's own command line carried `-HV 2021` (the original issue title was
`[hlsl 2021] Odd compiliation error`). It is preserved in `cmd-as-filed.txt` and
was dropped from `cmd.txt` only after measuring that it is inert — see
*History* below and `method-notes.md` §1.

Three predicates, because the symptom changes shape across the history:

| file | matches |
|---|---|
| `match.json` | the diagnostic quoted in the issue |
| `match-crash.json` | any internal failure |
| `match-fails.json` | `any_of` of the two — "this does not compile" |

`match-fails.json` is the one the history is measured on. The two narrow
predicates locate the boundary inside it. The composite also exists to keep
`classify()` from demoting valid probes: see `method-notes.md` §2.

## Ground truth — main-debug (1.9.0.5433, 13730886e)

```
[exit] 2158624797            (0x80AA001D, DXC_E_LLVM_CAST_ERROR)
--- stdout ---
--- stderr ---
Internal Compiler error: llvm::cast<X>() argument of incompatible type!
```

`out-main-debug--match-fails.txt`. No diagnostic, no source location.

The build was verified before use: `dxc --version` reports `1.9.0.5433`, and
`git diff --name-only ab5400907 13730886e` filtered to non-skill paths is empty
(control: the same query against `13730886e~500` reports 1102 files, so it can
detect a difference).

## Where it fails

`manual-case-cast-stack.txt`, captured with `cdb`:

```
dxcompiler!llvm::llvm_cast_assert_internal
dxcompiler!llvm::cast<llvm::LoadInst,llvm::User>
dxcompiler!`anonymous namespace'::LowerGetResourceFromHeap
dxcompiler!CGHLSLMSHelper::FinishIntrinsics
dxcompiler!`anonymous namespace'::CGMSHLSLRuntime::FinishCodeGen
```

Source corroboration: `tools/clang/lib/CodeGen/CGHLSLMSFinishCodeGen.cpp`,
`LowerGetResourceFromHeap` (defined ~278, called ~3527). It walks the users of
the heap-subscript result assuming each is a `BitCastInst` whose users are
`LoadInst`s, and casts without checking:

```cpp
LoadInst *LI = cast<LoadInst>(*(cuit++));
```

A member call on the cast expression produces a different user, so the cast
throws. Continuing past the throw in the debugger shows the consequence: the
`dx.hl.cast.handleToRes.float` call is never lowered and DXIL validation
rejects the module. Both halves are in `manual-case-cast-stack.txt`.

This is **not** a Debug-build artefact. `llvm_cast_assert` is defined
unconditionally in `include/llvm/Support/ErrorHandling.h:111` and throws
`hlsl::Exception(DXC_E_LLVM_CAST_ERROR, ...)`; all fifteen shipped Release
binaries from v1.7.2207 onward exit with the same `0x80AA001D`.

## Scope — measured, not inferred

| control | result on main |
|---|---|
| `control-local.hlsl` — subscript to a local, no cast (the 2021 workaround) | exit 0 |
| `control-cast-local.hlsl` — cast, assigned to a local, then call | exit 0 |
| `control-cast-arg.hlsl` — cast used as a call argument | exit 0 |
| `control-heap.hlsl` — feature-presence probe | exit 0 |
| `repro.hlsl` — member call **on** the cast expression | 0x80AA001D |

So neither the cast nor the heap subscript is the problem; the failing shape is
specifically a member call applied directly to the cast expression.

`manual-case-source-window.txt` shows why nothing caught it: the construct does
appear in three in-tree tests
(`hlsl/template/FunctionOverloads.hlsl`, `hlsl/template/InstantiateObjectMethods.hlsl`,
`hlsl/auto/auto-no-descriptor-heap.hlsl`), but the first two are `-ast-dump` and
the third is `-verify` with expected errors, so none of them reaches code
generation. 70 test files use the supported spelling.

## History — for as long as it is possible to check

Measured with `match-fails.json` across 20 stable releases (5 prereleases
excluded by policy; `v1.2.0-alpha` has no usable `dxc` asset).

| releases | outcome | exit |
|---|---|---|
| v1.4.1907, v1.5.2010 | `error: invalid profile ps_6_6` — for the repro **and** for `control-heap.hlsl`; genuine invalid probes | 0x80004005 |
| v1.6.2104, v1.6.2106, v1.6.2112 | the diagnostic quoted in the issue | 0x80004005 |
| v1.7.2207 … v1.9.2607 (15 releases) | internal compiler error | 0x80AA001D |
| main-debug | internal compiler error | 0x80AA001D |

**18 of 18 Shader Model 6.6-capable stable releases fail.** The regression
boundary is v1.6.2112 (2021-12-08) → v1.7.2207 (2022-07-18).

Only two releases are unprobeable, and both are demonstrated so rather than
assumed: `control-heap.hlsl` fails on them identically to the repro, which is
what distinguishes "too old for the feature" from "reproduces".

### The `-HV 2021` correction

The first pass reported the history as starting at v1.6.2112 — because
v1.4.1907, v1.5.2010, v1.6.2104 and v1.6.2106 answer `Unknown HLSL version:
2021` and are demoted, for a reason unrelated to the issue.
`manual-case-release-matrix.txt` runs all three cases on all 21 builds with and
without the flag: **51 comparisons byte-identical, 12 differing**, the 12 being
exactly the 4 flag-rejecting releases × 3 cases. That proves the flag inert
where it is accepted, and recovers v1.6.2104 and v1.6.2106 — extending the
measured history to **six months before the issue was filed**. The matrix has an
IDENTITY self-test that fails if only one of the two outcomes ever occurs.

### Regression window

248 commits between v1.6.2112 and v1.7.2207; 4 of them touch
`CGHLSLMSFinishCodeGen.cpp`, counted by file rather than by title. The failing
function is **byte-identical at both tags** (80-line comparison, with a control
comparison against a different function showing 79 of 80 lines differ, so the
comparison is not vacuous). No commit is named: the change that let the
construct reach this lowering is upstream of code generation and was not
isolated. Attributing it would need a build at a candidate commit, which was not
done.

## Compiler Explorer

https://godbolt.org/z/f59x8P75v — `dxc_1_6_2112` (the reported diagnostic),
`dxc_trunk` (the internal error), `hlsl_clang_trunk`. Full panes in
`manual-case-godbolt-verify.txt`. CE's Linux trunk build prints
`Internal Compiler error: cast<X>()…` where the local Windows build prints
`llvm::cast<X>()`; the local capture is the citable text.

The Clang pane answers a different question and answers it negatively:
`error: use of undeclared identifier 'ResourceDescriptorHeap'`. The successor
front end does not implement the feature yet, so it cannot be consulted on
whether this spelling should be accepted. `check-in-clang` is therefore *not*
proposed — the comparison has already been run.

## Assessment

- The issue is still live and now has a worse symptom than the one reported.
- The issue text is stale: the diagnostic it quotes has not been emitted by any
  release since v1.7.2207, and the 2021 comment reasoning about the diagnostic
  describes behaviour that no longer exists. A reader spot-checking the issue
  today sees a crash, not the reported error.
- The language question — should `((StructuredBuffer<float>)Heap[i]).Load(0)`
  compile? — is untouched by this triage. The 2021 comment says it should. Either
  answer requires the same first step: the compiler must stop failing internally.
- The workaround still works, so severity is bounded; the crash is not.

**Suggested action:** `still-valid-keep-open`.
**Suggested labels:** add `bug`, `crash` (currently unlabelled).
`hlsl2021` was considered and rejected on the equivalence evidence above.

## Files

| file | what it is |
|---|---|
| `expected.md` | the symptom, written before the compiler was run |
| `repro.hlsl`, `cmd.txt`, `cmd-as-filed.txt` | the repro and both command lines |
| `match.json`, `match-crash.json`, `match-fails.json` | the three predicates |
| `control-*.hlsl`, `variant-*.txt` | the scope table above |
| `out-*.txt` | one capture per release per predicate |
| `manual-case-release-matrix.txt` (+ `release-matrix.py`) | feature presence and `-HV 2021` equivalence |
| `manual-case-cast-stack.txt` (+ `capture-stack.py`) | the stack, and the state past the throw |
| `manual-case-source-window.txt` (+ `source-window.py`) | test coverage and the regression window |
| `manual-case-godbolt-verify.txt`, `godbolt-note.txt` | the published link, verified |
| `comment.md` | draft comment — **not posted** |
| `method-notes.md` | five observations about the method, for the next batch |
