# Method notes -- #5255 (batch-019)

- **Reusing #4273's `measure.py` release-matrix pattern for a second `dxr`
  issue confirms it generalises cleanly.** Copied the shape (stage the
  ground-truth `dxr.exe` next to each release's own `dxcompiler.dll` under a
  per-issue `.cache/rwNNNN/` scratch dir, score with `triage.classify` +
  this issue's own `match.json`), changed only the probes and the repro. No
  changes needed to `triage.py` itself. Worth promoting into SKILL.md as the
  canonical harness-as-compiler release-matrix template for `dxr`
  specifically (the existing SKILL.md text already generalises this for PIX
  passes/reflection DLLs; a `dxr`-specific one-line pointer at "#4273's
  release-matrix pattern" would save the next `dxr` issue from re-deriving
  it, the way I did not have to).

- **A ground-truth verification can complete without any rebuild by reusing
  an already-built sibling binary that shares the same `dxcompiler.dll`.**
  This issue's tool (`dxr.exe`) was not present in `build/Debug/bin/` (a
  prior batch's `dxr` build there had gone stale/missing), and the task
  forbade rebuilding. `build/Release/bin/dxr.exe` and `dxc.exe` both
  self-report the exact target commit prefix (`89e2f98e2`), because they
  load the same `dxcompiler.dll` where the version string and the bug itself
  both live. This is a variant of "verify by tree, not by SHA" worth a
  one-line generalisation: for a bug inside `dxcompiler.dll`, ANY co-located
  driver that loads it (dxc, dxr, dxa, dxopt, ...) is equally good evidence
  of the DLL's provenance, which is a cheap way to avoid a rebuild when the
  usual driver binary is unavailable read-only.

- **A closed-but-correct fix PR is not a rare shape.** This is the second
  issue in the tree (after #2427) where the actionable fact is not "does it
  still reproduce" (yes) but "a correct fix already existed and lapsed
  unmerged, for reasons unrelated to correctness" -- here, a two-year
  inactivity sweep, not a technical rejection. Worth flagging at collation
  as a pattern to check for explicitly: `gh api .../timeline` for a
  cross-referenced PR, then `gh pr view --json mergedAt,state` on it, before
  concluding an issue only needs "still repros" as its answer.

No predicate, tooling, or classifier defects found on this issue; nothing
here required a `triage.py`/`SKILL.md` change, only additive artifacts under
`data/issues/5255/`.
