# #5595 — [Feature Request] support hash stability test in lit

## Summary

Not a compiler bug: this is a test-infrastructure feature request. It asks for a `lit`
test format that provides the coverage the TAEF-based `CodeGenHashStability*` tests give
today (recompiling each test shader with hash-sensitive flag variants and comparing output
container hashes), so that individual `.hlsl`/`.ll` files can be moved from
`tools/clang/test/HLSLFileCheck` (TAEF-only today) into
`tools/clang/test/HLSLFileCheckLit` (lit) without losing that coverage. There is no shader
repro and no compiler command line to run — `dxc` is not the instrument here, the lit
configuration is (`godbolt` correctly has nothing to publish; skipped, see verdict).

**As of ground truth `main-debug` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df), the request is
still unimplemented** and the issue text still accurately describes the gap. Concretely
(full commands and output in `manual-case-lit-hash-absence.txt`):

- No lit-native hash-stability mechanism exists in the tree: no `DxcHashTest` lit format
  class, no `HashStability.py`, no `%hash_stability` substitution, nothing under
  `utils/lit/lit/formats/` beyond `base`, `googletest`, `shtest` and `taef`.
- `tools/clang/test/HLSLFileCheckLit` holds 29 tracked files; none carries a hash directive.
  `tools/clang/test/HLSLFileCheck` (TAEF-only, hash-tested today) holds 2212.
- The existing hash-stability tests are 10 TAEF `TEST_METHOD`s in
  `tools/clang/unittests/HLSL/CompilerTest.cpp`
  (`CodeGenHashStability{D3DReflect,Disassembler,DXIL,HLSL,Infra,PIX,Rewriter,Samples,
  ShaderTargets,Validation}`), each iterating its own subfolder under
  `..\HLSLFileCheck\` via `CodeGenTestCheckBatchHash` and hashing every `.hlsl`/`.ll` file
  found (`CompilerTest.cpp:279-288`, `:428-470`; the hash test itself dispatches through
  `RunHashTestFromFileCommands` → `RunDxcHashTest`, `FileCheckerTest.cpp:1369-1383,379`).
- `utils/lit/lit/formats/taef.py` (`TaefTest`) *is* a lit format that wraps whole TAEF
  test methods so `lit` can discover and execute them — including the existing
  `CodeGenHashStability*` methods, since they inherit the class-level `Priority=0`
  property (`CompilerTest.cpp:143-146`) and so pass the runner's default
  `@Priority<1` filter (`tools/clang/test/taef/lit.cfg:46-55`). That is a different thing
  from what the issue asks for: it lets the *existing whole-suite* TAEF hash test run
  as one opaque pass/fail unit under `lit`, but it does nothing to let a single lit
  `.hlsl` file (e.g. one already moved to `HLSLFileCheckLit`) get its own hash-stability
  check the way a `HLSLFileCheck` file gets today, and does not unblock moving files out
  of `HLSLFileCheck`. See `expected.md` for why this does not count as resolving the
  request.

## The proposed fix stalled in review, unmerged

Two related issues exist: #5552 ("Support hash stability testing through LIT", filed
2023-08-15) was closed 2023-08-30 as "Duplicated by #5595" (the surviving/tracking issue is
this one, #5595, filed 2023-08-24).

PR #5600, "[lit] Add hash stability test for lit." (opened 2023-08-24, same day as this
issue, body says "Fixes #5595"), added exactly the kind of mechanism the issue asks for: a
new lit format `DxcHashTest` that scans all HLSL files under `tools\clang\test`, compiles
each twice (with/without `-Zi`) and compares container hashes, with a
`hash_stability_path` param to scope a debug run.

The PR received substantial maintainer review (34 review threads, `llvm-beanz` and
`pow2clk` participating) across three weeks, including one `APPROVED` review from
`llvm-beanz` on 2023-09-05 followed nine minutes later by `CHANGES_REQUESTED` from the same
reviewer after further discussion. The last unresolved thread (`llvm-beanz`,
2023-09-05T17:50:21Z) raises a design objection that was never settled: the new format does
not traverse using lit's normal shell-test flow and does not respect lit local configs the
way the reviewer expected, which surfaced two real hash mismatches
(`HLSLFileCheck/hlsl/control_flow/return/lifetime-markers.hlsl` and
`HLSLFileCheck/hlsl/objects/Cbuffer/retCBV3.hlsl`) that the author worked around by disabling
those two tests rather than resolving the underlying local-config question (full thread in
`manual-case-pr5600-unresolved-threads.txt`).

The PR's last commit is 2023-09-22 ("Create tmp dir for original output like Fi/Fe",
`cd69ffc8e37c673bc117c6248d56a44875f96e45`). `gh pr view 5600` reports
`state: OPEN`, `mergedAt: null`, `mergeCommit: null` as of this triage. Fetching the PR's
head directly from `upstream` and testing ancestry confirms it directly rather than relying
only on the API fields:
```
$ git fetch upstream pull/5600/head
$ git rev-parse FETCH_HEAD
cd69ffc8e37c673bc117c6248d56a44875f96e45
$ git merge-base --is-ancestor FETCH_HEAD HEAD
(exit 1)
```
Exit 1 means the PR's own final commit is not an ancestor of this branch's `HEAD` — the PR
was never merged, consistent with the tree-search evidence above and with the API state.
(Full transcript: `manual-case-lit-hash-absence.txt`, section 6.)

**Conclusion:** the community both wanted and attempted this feature (two issues, one
PR with substantial review), the attempt surfaced a real design problem the reviewer flagged
as wrong, and the fix was never carried to completion. `still-valid-keep-open` with
`needs-human-judgement`/`up-for-grabs` framing is appropriate; the issue's own text remains
accurate and not stale (it does not claim the fix landed, and nothing about "moving taef
FileCheck test to lit FileCheck test" being blocked has changed).

## Not-compiler-verifiable rationale

Per SKILL.md step 5/7: this is a test-infrastructure/tooling question, not a shader-compile
question. No `cmd.txt`/`match.json` is written (none would be meaningful — there is no
compiler command whose output would confirm or refute a *lit test-runner* capability), and
`godbolt` is skipped: Compiler Explorer compiles a single HLSL source through a fixed set of
compiler panes; it cannot express "does the local `lit` invocation support hash-stability
testing", and this issue has no shader repro. All evidence is filesystem/repository-history
based and captured in the `manual-case-*.txt` files, generated by the two committed scripts
(`check-lit-hash-support.py`, `fetch-github-evidence.py`, `fetch-review-threads.py`) so a
reader can regenerate every line.
