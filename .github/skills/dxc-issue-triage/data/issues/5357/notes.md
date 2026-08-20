# Notes — #5357: Ensure type annotations are added for reference returning intrinsics/operators

## Ground truth

`main-debug` at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (public upstream `main`), Debug
config. `dxc --version`: `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
7665270b9)` — self-reports a fork-local commit, but the registered `git_commit` field and the
compiler's cached JSON tie the build to the cited public SHA
(`.cache/compilers/main-debug.json`), which was verified as an ancestor of the working tree
before this session started (`git merge-base --is-ancestor` exits 0).

## What the issue asks

Open-ended tech debt from llvm-beanz: when an intrinsic/operator returns a reference to an
object that isn't otherwise guaranteed to be type-annotated, and the caller chains straight
into another member call rather than binding the result to a local, no type annotation is
added — because the annotation path lives in `EmitAutoVarAlloca`, which only runs for a bound
local. The action requested is "find what else this gap might impact, write a test for that,
and fix it," not a single fix for one call site.

## History inside the thread

- The issue was originally triggered by `NodeOutputArray::operator[]` returning a reference
  (work-graphs/#5358). #5358 was fixed by changing that operator to return a value instead —
  tex3d confirms in this thread (2024-01-24) that this removes the *triggering* case but not
  the underlying annotation gap, and the issue was explicitly kept open and dropped from the
  SM 6.8 milestone as "not a regression."
- 2024-01-31: tex3d posts a concrete repro (below) and says it still crashes.
- 2024-01-31: tex3d opens PR **#6227** "Add type annotations for missing HLSL object cases"
  (body: "Fixes: #5357"), covering node-object method return types and type template
  arguments; the PR's own description lists "TODO: Add tests." `gh pr view 6227` shows it is
  still **open and marked draft**, last updated 2024-03-07 — over two years stale relative to
  this triage — and unmerged.
- anupamachandra (2024-01-31) confirms the underlying gap remains even after the operator fix,
  attributing the *current* (2024) working case to an unrelated `recordSizeWAR` workaround
  added in `AddOpcodeParamForIntrinsic`, not to a real fix of the annotation gap.

## Repro and measurement

`repro.hlsl` / `cmd.txt` reproduce tex3d's posted case verbatim (`-T lib_6_8`):

```hlsl
struct RECORD1 { uint value; };
[Shader("node")] [NodeLaunch("broadcasting")] [NodeDispatchGrid(1,1,1)] [NumThreads(128,1,1)]
void node_1_1([NodeArraySize(128)] [MaxRecords(64)] NodeOutputArray<RECORD1> OutputArray) {
    OutputArray[1].GetThreadNodeOutputRecords(2).OutputComplete();
}
```

This chains `GetThreadNodeOutputRecords(2)` directly into `.OutputComplete()` — no
intermediate `ThreadNodeOutputRecords<RECORD1>` local, which is exactly the shape the thread
says skips the annotation path. Every pre-existing FileCheck test in
`tools/clang/test/HLSLFileCheck/hlsl/workgraph/nodeoutputarray.hlsl` uses the same API only
through a bound local, so none of them exercise this.

`match.json` uses `internal_failure` (per skill guidance: use this kind for anything
crash-shaped, not a text match on one build's assert message).

**`main-debug` (Debug, ground truth):** exit `3758096385` (`0xE0000001`, C++-exception-style
assert) — `out-main-debug.txt`. Debugger stack (`manual-case-assert-stack.txt`, captured via
`capture-stack.py`, which echoes the exact `cdb` invocation run):

```
Error: assert(pAnno != nullptr && pAnno->GetNumTemplateArgs() == 1 &&
       "otherwise the node record template is not declared properly")
File: tools/clang/lib/CodeGen/CGHLSLMSFinishCodeGen.cpp(1071)
Func: `anonymous-namespace'::AddOpcodeParamForIntrinsic
```

This is precisely the function anupamachandra named in the thread
("`AddOpcodeParamForIntrinsic` function in `CGHLSLMSFinishCodeGen.cpp`") — `pAnno` (the node
record's type annotation) is null exactly because it was never added for the chained,
unbound intermediate. This ties the crash to the mechanism the issue describes, not merely to
"some assert."

**Control** (`control-with-temp.hlsl` — same shader, but binds
`GetThreadNodeOutputRecords(2)` to a `ThreadNodeOutputRecords<RECORD1> outRec` local first, the
documented workaround and the shape every pre-existing test uses): exit `0`, no diagnostic —
`variant-control-with-temp-main-debug.txt`. `--expect no-match` held. This is the discriminating
control: it isolates "chained, unbound reference result" as the one variable that changes the
outcome.

**Release-build signature differs, same root cause — one `internal_failure` predicate covers
both:**

- `v1.8.2403` (oldest stable release that accepts `lib_6_8`): exit `3221225477`
  (`0xC0000005`, access violation) — `out-v1.8.2403.txt`.
- `v1.9.2607` (newest catalogued stable release): exit `3221225477`, `Internal compiler error:
  access violation. Attempted to read from address 0x0000000000000028` — `out-v1.9.2607.txt`.
  Offset `0x28` from a null base is consistent with dereferencing the same null `pAnno` the
  Debug assert guards, with the check compiled out under `NDEBUG` (the general pattern
  documented in the skill for #3259: an assert that is Debug-only does not mean the underlying
  defect is).
- Compiler Explorer `dxc_trunk` (Linux Release): exit `139`, `Program terminated with signal:
  SIGSEGV` — same defect, third platform/build-configuration, third exit-code family, one
  predicate (`manual-case-godbolt-verify.txt`).

## History across releases (`bisect --issue 5357`)

Every stable release through `v1.7.2308` answers `error: invalid profile lib_6_8` — a genuine
feature-absence rejection (`invalid-probe`, verified from the captured text in
`out-v1.7.2308.txt`, not inferred), since Work Graphs/`lib_6_8` did not exist yet. 5
prereleases (including 2 mesh-nodes/work-graphs previews) are excluded from the search by
policy — none is named explicitly in the issue text, so none opts in. `v1.8.2403` (first stable
release exposing `lib_6_8`) and `v1.9.2607` (newest catalogued stable release) both reproduce.

**Result: always-repro'd for as long as the feature has existed in a stable release
(`v1.8.2403` .. `v1.9.2607`), and still reproduces on current `main` (`89e2f98e2`).** The
9 older releases skipped were never able to express the feature at all, not evidence of a fix
window; CE's `dxc_1_6_2112` pane is presented for the same reason and not read as clean.

## Compiler Explorer

`https://godbolt.org/z/eqjMv4v5Y` (verified via short-link read-back; `godbolt-note.txt`
explains what to look for — the absent diagnostic and SIGSEGV on `dxc_trunk`, not the expected
"invalid profile" pane on `dxc_1_6_2112`).

## Assessment

The issue's headline claim — reference-returning intrinsics/operators can skip type
annotation when chained without a bound local — is not just plausible, it is independently
confirmed with a concrete, currently-crashing instance, at the exact function
(`AddOpcodeParamForIntrinsic`) a maintainer named in the thread two years ago. The proposed fix
(#6227) has been open and in draft, without tests, for over two years and is unmerged. This is
still `still-valid-keep-open`, not `close-fixed`: the specific instance in this thread remains
broken, and the issue's own scope ("find what else this gap might impact") is broader than one
instance and not something a single clean compile could close even if this one call site were
fixed.

## Labels

Current: `tech-debt`. The evidence now includes a reproducing, currently-uncontested internal
crash (assert in Debug, access violation in Release, SIGSEGV on CE/Linux) — that is squarely
what `bug` ("Bug, regression, crash") and `crash` ("DXC crashing or hitting an assert") are for,
and `tech-debt` alone understates it. `tech-debt` is kept because the broader ask (audit every
reference-returning intrinsic/operator) remains open work beyond this one confirmed instance.
No routing label change proposed beyond that: `sm6.8` is not added, since neither the label
description nor a comparable closed sibling issue (#5358, unlabelled) establishes it as this
repo's convention for Work Graphs issues, and guessing a routing label from a hunch is exactly
what step 8 says not to do.

## What this triage could not determine

- Whether the annotation gap has a second, non-node-object trigger elsewhere in the compiler
  ("what else this type annotation gap might impact") — the issue's own open question, not
  settled by one confirmed repro.
- Whether PR #6227 (still draft, still missing its own promised tests) fixes this exact repro;
  it was not built or tested here, per the "no shared rebuild" boundary for this session.
- `reviewed_by`: pending — a second-model review of this draft has not yet been run in this
  session (batch-019 collation records it separately).
