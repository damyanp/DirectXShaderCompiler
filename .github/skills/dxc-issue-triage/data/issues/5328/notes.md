# Notes — issue #5328

## Ground truth

Compiler `main-debug`, registered `git_commit = 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
exe `build/Debug/bin/dxc.exe`. The binary self-reports version
`1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)` —
i.e. a local branch commit `7665270b9`, not the cited public SHA. Per
the skill's provenance rule this is expected and was verified by tree,
not by trusting `--version`:

* `git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
  restricted to outside `.github/skills/dxc-issue-triage/` → **0 files
  differ**.
* Control: the same diff against the shallow clone's oldest reachable
  commit (`8a8b29f967b5925a970949984442b3783d730551`) → **1027 files
  differ**, proving the check can detect real differences (it is not
  vacuously empty).
* Re-verified from a durable, re-runnable artifact:
  `manual-case-source-check.py` / `.txt` re-runs
  `git diff --name-only HEAD 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
  and records `0` differing files outside the skill directory.

The repo is a shallow clone (483 commits reachable from ground truth);
the oldest reachable commit is `8a8b29f967b5925a970949984442b3783d730551`,
which limits how far back `git blame`/`git log -S` can date anything.

## The reported typo — confirmed present, unchanged

`lib/HLSL/HLMatrixBitcastLowerPass.cpp`, `HLMatrixBitcastLowerPass::lowerMatrix`,
line 244 (line ~229 at filing time):

```cpp
} else if (StoreInst *ST = dyn_cast<StoreInst>(U)) {
  Value *V = ST->getValueOperand();
  if (VectorType *Ty = dyn_cast<VectorType>(V->getType())) {
    IRBuilder<> Builder(LI);   // should be Builder(ST)
```

`manual-case-source-check.txt` shows both occurrences of the literal
text `IRBuilder<> Builder(LI);` in this file: line 217, inside the
`LoadInst *LI` arm (correct — `LI` is valid there), and line 244,
inside the sibling `StoreInst *ST` arm (the bug — `LI` was never
assigned in this iteration, since the earlier `dyn_cast<LoadInst>`
failed, which is exactly why control reached the `StoreInst` arm at
all). The script's own context dump confirms the two arms are mutually
exclusive branches of the same `if`/`else if` chain (`dyn_cast<LoadInst>`
in the 20 lines above line 217, `dyn_cast<StoreInst>` in the 20 lines
above line 244, never both).

`IRBuilder<>`'s single-`Instruction*` constructor
(`include/llvm/IR/IRBuilder.h` ~line 546) is
`explicit IRBuilder(Instruction *IP, ...) : IRBuilderBase(IP->getContext(), ...)`
— it dereferences `IP` immediately via `getContext()`. Passing the
guaranteed-null `LI` therefore crashes deterministically and
immediately, every single time this branch executes; this is not a
"might be null" risk, it is an unconditional null dereference on entry.

`git blame -L 244,244` → `^8a8b29f96` (the shallow-clone boundary
commit, 2025-06-03), i.e. the typo predates the locally reachable
history and cannot be dated further back from this clone.

## Reachability

`MatrixBitcastLowerPass` is registered only at
`lib/HLSL/DxilLinker.cpp:1272`, inside `DxilLinkJob::RunPreparePass`
(confirmed: the only two hits for `createMatrixBitcastLowerPass` in the
repo are the pass's own definition and this one call site). So this
code path only runs for `dxc -T lib_6_x -link ...`, never for an
ordinary single-module compile.

`RunPreparePass`'s pipeline runs `AlwaysInlinerPass` *before*
`MatrixBitcastLowerPass`. The existing test
`tools/clang/test/HLSLFileCheck/dxil/linker/lib_mat_entry.hlsl` shows
the exact caller-side bitcast pattern the pass's own header comment
describes (`bitcast [24 x float]* ... to [2 x %class.matrix.float.4.3]*`),
confirming the "fake matrix pointer over real flat/vector storage"
mechanism this pass targets is real and exercised elsewhere in the
test suite — for a cbuffer-backed matrix array passed by value to an
externally-declared, undefined-in-that-TU function (so nothing can be
inlined).

## Repro attempts and their outcome (negative result, but instructive)

`link-a.hlsl` / `link-b.hlsl` + `manual-case-link-attempt.py` /
`.txt`: an exported `storeMat(inout float2x2 arr[16], int idx)`,
linked against a compute-shader caller that indexes a **groupshared**
matrix array at a **dynamic**, buffer-sourced index (to discourage
constant-folding/unrolling), via `dxc -T lib_6_9 -link ...`. Result:
**exit 0, no crash**, in every variant tried (originally a 4-element
array with a manual copy loop; then a 16-element array relying on
HLSL's own inout copy-in/copy-out; then re-linking with
`-exports "storeMat;main"` to keep `storeMat` individually exported).

The captured `.ll` shows why: `storeMat` is fully inlined into `main()`
by `AlwaysInlinerPass` regardless of `export`/multi-export status —
because the final linked output resolves to a single self-contained
compute shader entry point, every reachable function must eventually
be inlined into it, and `AlwaysInlinerPass` does this *before*
`MatrixBitcastLowerPass` runs. `SROA`/mem2reg then resolves the entire
inlined copy-in/copy-out to plain `<4 x float>` loads/stores. No
fake-matrix-typed `StoreInst` ever reaches
`HLMatrixBitcastLowerPass::lowerMatrix` in this configuration —
`MatrixBitcastLowerPass`, running immediately after, finds nothing left
to do.

This does not mean the bug is unreachable in general — `lib_mat_entry.hlsl`
proves the underlying bitcast mechanism is real for library-target
outputs that are *not* fully resolved to one entry point (e.g. a
still-multi-export linked library, or a call to a function whose body
is never linked in at all) — only that constructing a *minimal*,
single-entry-point trigger for the specific `StoreInst` branch within
the time available for this triage was not achieved. This is recorded
as a genuine limitation, not elided.

**Method observation (see also `method-notes.md`):** a naive
`dxc -T lib_6_x -link` repro attempt aimed at a pass that runs late in
`RunPreparePass` must account for `AlwaysInlinerPass`, which runs
first and aggressively eliminates cross-module call boundaries whenever
the final link target is a single shader entry point (as opposed to a
still-multi-export library target). "Any `-link` scenario" is not
sufficient; the storage/indexing pattern must survive past inlining
*and* the link output must not collapse to one function.

## The 2026-04-27 comment is a different, unrelated bug

`variant-comment-repro.hlsl` (mandryskowski's tint-generated HLSL,
copied verbatim from the comment) does crash ground truth
(`dxc -T cs_6_0 -E main`), confirmed with exit `-536870911` ==
`0xE0000001`. `manual-case-comment-crash-stack.txt` captures the `cdb`
stack: the fault is `HLMatrixLowerPass::replaceAllVariableUses` (via
`lowerAlloca` → `runOnFunction`) → `IRBuilder::CreateGEP` →
`GetElementPtrInst::Create` → `checkGEPType`, asserting in
`include/llvm/IR/Instructions.h`. That is **`HLMatrixLowerPass.cpp`,
not `HLMatrixBitcastLowerPass.cpp`** — a different file, different
function, different fault, and (per the reachability analysis above)
a codepath that doesn't even require `-link`. This crash is real and
confirmed, but it is very likely a misattached/misdiagnosed comment on
this issue rather than corroborating evidence for the reported typo.
It is not used anywhere in the verdict below.

**Method observation:** a comment posted on an issue can describe a
confirmed-reproducing crash that is nevertheless a completely different
bug from the one the issue reports (different file, function, and
fault). Verify a comment's stack trace against the issue's actually
named file/line before treating it as corroborating evidence — the
comment's *symptom class* (a matrix-related crash) matched, but nothing
about the crash's origin did.

## Predicate / `match.json`

None recorded. Per the skill's guidance, `match.json`/`cmd.txt` may be
deliberately absent when compiler output cannot answer the question. No
runtime trigger for the exact reported code path was constructed (see
above), so there is no dxc invocation whose stdout/exit-code would
correctly discriminate "typo present" from "typo fixed" — a predicate
built on any of the attempted repros would either measure the unrelated
`HLMatrixLowerPass` crash (comment b) or measure nothing (the
`-link` attempts, which never reach the buggy branch either way). The
verdict instead rests on the durable, re-runnable source-level checks
in `manual-case-source-check.py`, corroborated by control-flow/API
reasoning (`IRBuilder` constructor semantics) that is independent of
any input shader.

## Bisection

Not run. There is no working `cmd.txt`/predicate to bisect (see
above), and a source-text check across binary release assets cannot
answer "when did the typo appear" (releases are prebuilt binaries, not
source trees) — this would need a real, deeper (non-shallow) clone.
`git blame` already establishes the typo predates this clone's boundary
(`8a8b29f96`, 2025-06-03) on ground truth, which is the strongest
history statement available from this repository state.

## Compiler Explorer

Skipped — `MatrixBitcastLowerPass` only runs during multi-module
`-T lib_6_x -link ...`, and CE compiles a single file per pane with no
linking step, so CE cannot demonstrate the reported code path at all.
See `godbolt.txt`/the `--skip` recorded via `triage.py godbolt`.

## Labels

Current: `matrix-bug`, `tech-debt` — both accurate. Proposing to add
`crash` (the code, once reached, is a guaranteed, unconditional
null-pointer dereference — this is a real crash bug, not merely a style
nit, even though a minimal trigger wasn't constructed here) and
`shader-linking` (the entire bug lives in a pass that exists
exclusively for `-T lib_6_x -link`, matching that label's own
description precisely). No removals proposed.

## Verdict summary

* **Status:** `repros` — the reported defect (the exact source text,
  in the exact guaranteed-null-dereference configuration) is present,
  unchanged, on ground truth `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.
* **Repro quality:** `partial` — complete, unambiguous source-level
  diagnosis; no reporter test case; agent-constructed runtime triggers
  attempted and documented as unsuccessful within the time budget.
* **History:** `always-repro'd` (as far back as this shallow clone can
  show — predates the clone's boundary commit).
* **Confidence:** `high` for the static claim (exact code + API
  semantics leave no room for the null deref not occurring once the
  branch is reached); the *practical reachability* of the branch from
  an actual HLSL library is not fully established by an executed
  crash, which is why repro-quality is `partial` rather than
  `complete`.
* **Suggested action:** `still-valid-keep-open`. The fix (`Builder(ST)`
  instead of `Builder(LI)`) is a one-token change wherever it is
  reachable at all; this is an easy, low-risk correctness fix a
  maintainer can make without needing anyone's specific input shader.
