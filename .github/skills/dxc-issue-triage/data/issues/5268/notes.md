# #5268 — Rewriter removes a static global that a surviving global's initializer needs

## Ground truth

`main-debug`, registered at public commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(`1.9.0.5465 (triage, 7665270b9)`). Local HEAD is a different fork-local commit; provenance was
verified by tree, not by SHA:

- `git diff --name-only origin/main HEAD` → 0 files outside `.github/skills/dxc-issue-triage/`.
- Control: `git diff --name-only origin/main^ HEAD` → 1 file outside that dir
  (`tools/clang/unittests/HLSLExec/LinAlgTests.cpp`), matching `89e2f98e2`'s own title
  ("[HLSL] Add LinAlg descriptor I/O offset..."), proving the check can detect a real
  difference and isn't vacuously clean.
- `build\Debug\bin\dxc.exe --version` self-reports the exact registered version string.

`dxr.exe` (the standalone rewriter the issue actually exercises) is only built in
`build\Release\bin\` locally. Its `--version` self-reports `(main, 89e2f98e2)` — the same
commit — with no `-dirty` suffix, so it is valid ground truth for this issue. Debug-vs-Release
matters mainly for asserts; this is an ordinary diagnosed compile error, not a crash, so the
Release rewriter binary is fine.

## The repro

Issue body, verbatim (repro quality: **complete**, see `expected.md`):

```
dxr test.hlsl -E VSMain -remove-unused-globals
```

```hlsl
static const float POINT_SIZE = 3.0f;
static const float3 POINT_SIZE_3 = float3(1.0f, 1.0f, 1.0f) * POINT_SIZE;
...
```

`VSMain` uses `POINT_SIZE_3`, whose own initializer references `POINT_SIZE`. The claim is that
the rewriter's `-remove-unused-globals` pass keeps `POINT_SIZE_3` (correctly, since it's used by
the entry point) but still drops `POINT_SIZE` (incorrectly, since `POINT_SIZE_3`'s initializer
needs it), producing rewritten source that fails to recompile.

## Root cause (source-corroborated)

`tools/clang/tools/libclang/dxcrewriteunused.cpp`. `CollectRewriteHelper` walks reachable code
from the entry point via `VarReferenceVisitor` to build the set of globals to keep.
`VarReferenceVisitor::VisitDeclRefExpr` (~line 147–179), on finding a reference to a used
global, tries to also mark that global's *own initializer's* references as used — but it only
recurses into an initializer that is exactly an `InitListExpr`, `ImplicitCastExpr`, or
`DeclRefExpr`. `POINT_SIZE_3`'s initializer, `float3(1,1,1) * POINT_SIZE`, is none of those
(a `BinaryOperator`/`CXXOperatorCallExpr`), so the visitor never walks into it, the reference to
`POINT_SIZE` is never discovered, and `POINT_SIZE` is removed as "unused" even though it isn't.

This is a real gap in the traversal, not something specific to multiplication — any compound
initializer expression (vector construction, arithmetic, function calls) on a kept global will
hide a transitive reference the same way.

## Harness

`dxr.exe` is not `dxc.exe` and can't be driven through the normal `cmd.txt`-over-registered-`dxc`
path, so it's wrapped per the SKILL.md "harness-as-compiler" pattern (as used for
`main-debug-pix`): `harness.py`/`harness.cmd` run `dxr.exe` with the issue's exact arguments,
capture the rewritten HLSL, then recompile *that* with `build\Debug\bin\dxc.exe -T vs_6_0
-E <entry>`, printing both stages plus a harness-owned classification line
(`# dxc (recompile) classification: success|diagnosed-error|internal-failure|other:0x...`).
Exit codes are intentionally small and fixed (0/1/2) rather than relaying the raw recompile
HRESULT through `sys.exit` — `sys.exit(0x80004005)` silently corrupts to `0xFFFFFFFF` on
Windows because the value exceeds `INT32_MAX`; the classification text, not the process exit
code, is what `match.json` scores. Registered as `main-debug-dxr`
(`triage.py compiler --id main-debug-dxr --exe harness.cmd --commit 89e2f98e2...`).

`match.json` is `all_of`:
1. the harness's own `# dxc (recompile) classification: diagnosed-error` marker, and
2. `regex "use of undeclared identifier 'POINT_SIZE'"` as an anti-vacuity anchor, so an
   unrelated diagnosed error on the recompile can't satisfy the predicate for free.

## Primary probe

`out-main-debug-dxr.txt` (`main-debug-dxr`, `-E VSMain -remove-unused-globals repro.hlsl`):
`dxr.exe` drops `POINT_SIZE` and keeps `POINT_SIZE_3`'s initializer referencing it; the
recompile fails with `use of undeclared identifier 'POINT_SIZE'; did you mean 'POINT_SIZE_3'?`.
**Verdict: repro.** Matches `expected.md` exactly.

## Controls

- `control-single-level.hlsl` (one static global, no transitive chain): rewriter keeps it,
  recompiles clean. `variant-control-single-level-main-debug-dxr.txt`, `--expect no-match` →
  scored `no-repro` as expected.
- `control-chain-both-unused.hlsl` (same two-global chain, but neither reachable from the entry
  point): rewriter removes both cleanly, recompiles clean.
  `variant-control-chain-both-unused-main-debug-dxr.txt`, `--expect no-match` → scored
  `no-repro` as expected.

Together these show the predicate doesn't fire on an unrelated diagnosed error or a case where
the rewriter behaves correctly — only on the specific transitive-reference failure.

## Release history

`bisect` refuses a harness-as-compiler issue (it would substitute each release's own `dxc.exe`
for the harness rather than for the wrapped `dxr.exe`+`dxc.exe` pair). Instead,
`measure_release_history.py` drives an issue-local matrix: for each catalogued stable release,
it runs *that release's own* cached `dxr.exe` (from a pre-existing `.cache/rw4273/<tag>/`
per-release cache — provenance unknown, but independently verified: `--version` for
spot-checked tags matches known historical commit SHAs, e.g. v1.6.2104 = `e09a454eb`,
v1.6.2106 = `dad1cfc30`, and behavior is self-consistent on a known-good rewriter test file),
then recompiles the result with that *same* release's own `dxc.exe` — never cross-pairing
releases, per the #2918/#2922/#2923 precedent. Full transcript and summary matrix in
`manual-case-release-history.txt`.

Official release zips (`.cache/compilers/releases/<tag>/bin/x64/`) never bundle `dxr.exe`
(only `dxc.exe`/`dxcompiler.dll`/`dxil.dll`/`dxv.exe`), which is why this separate cache exists.

Result, oldest to newest:

| release | result |
| --- | --- |
| v1.4.1907 | **invalid-probe** — its `dxr.exe` fails *any* `-remove-unused-globals` invocation, even a known-good existing rewriter test, with a generic `Compilation failed - error code 0x80070057`; the flag is unusable in this release regardless of the reason, so it cannot exercise the code path under test |
| v1.5.2003 | excluded — a named prerelease with no cached `dxr.exe`; excluded by the standing prerelease policy (not explicitly named in the issue text, so no `release-policy.json` opt-in applies) |
| v1.5.2010 – v1.9.2607 (19 remaining stable releases) | **all repro**, identical diagnostic |
| main-debug (`89e2f98e2`) | **repro** |

Conclusion: **always-repro'd** across every stable release that can functionally probe this
flag (v1.5.2010 through v1.9.2607) and on main-debug; v1.4.1907 is an invalid-probe rather than
a clean result.

Caveat: this matrix is a hand-run script, not `triage.py bisect`/`run`, so it is outside
`reindex`'s automatic re-scoring (per SKILL.md's "What `reindex` guarantees, and what it does
not"). The primary probe and both controls *are* registered `run` captures and will be
re-scored normally.

## Compiler Explorer

Skipped (`godbolt --skip`, recorded in the DB). The defect is in the standalone `dxr.exe`
rewriter's `-remove-unused-globals` pass; Compiler Explorer only exposes `dxc`-style compiler
panes, and `dxc.exe` itself rejects the flag outright:
`dxc failed : Unknown argument: '-remove-unused-globals'` (verified locally,
`build\Debug\bin\dxc.exe -remove-unused-globals ...`). No CE pane, DXC or Clang, can run the
tool under test, so there is nothing a link could show.

## Labels

`labels --refresh` then `labels --issue 5268`: current `bug, rewriter`, proposed no additions
or removals. Both are already correct and specific (`rewriter` — "Bugs in the rewriter" — is
exactly what this is).

## Confidence

**High.** Root cause is identified in source (not just inferred from behavior), the primary
probe and two controls are captured and reproducible through `triage.py run`, and the defect
reproduces identically across every functionally-probeable stable release plus main-debug, with
a well-understood reason (v1.4.1907's `-remove-unused-globals` is generically broken) for the
one excluded release.

Suggested action: **still-valid-keep-open**.
