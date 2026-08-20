# Issue #5721 -- notes

## Claim

`IDxcLinker::Link(..., args={-Zi,-Qstrip_debug})`, `QueryInterface`d to
`IDxcResult`, never exposes a `DXC_OUT_PDB` output: `GetOutput(DXC_OUT_PDB,
...)` returns `E_INVALIDARG`. Reporter notes PR #5678 added some additional
linker outputs but not PDB.

## Cross-reference found

`gh api .../issues/5721/timeline` shows PR #6834 ("Add PDB output to
linker"), whose description says `Fixes #5721`. `gh pr view 6834` shows it
is **OPEN, not merged** -- so whatever it does is not on `main` as of the
ground-truth commit for this batch. This immediately suggested the bug is
still present on ground truth and gave a concrete place to look for the
root cause.

## Root cause (source read, no build needed)

`tools/clang/tools/dxcompiler/dxclinker.cpp`, in `Link()`'s output
assembly (~line 433), builds `DXC_OUT_OBJECT`, `DXC_OUT_ROOT_SIGNATURE`,
`DXC_OUT_SHADER_HASH`, and `DXC_OUT_REFLECTION` via `SetOutputObject(...)`
(these are the outputs PR #5678 added), immediately followed by a bare
`// TODO: DFCC_ShaderDebugName` comment where a `DXC_OUT_PDB`
`SetOutputObject` call would need to go. There is no code path in this
function that ever sets a `DXC_OUT_PDB` output object on the linked
result -- PDB was simply never wired up here, unlike the sibling outputs.

`include/dxc/Support/dxcapi.impl.h`'s `GetOutput(DXC_OUT_KIND, ...)`
returns `E_INVALIDARG` whenever the requested slot's `object.kind ==
DXC_OUT_NONE`, i.e. was never `SetOutputObject`'d -- exactly the reporter's
observed `E_INVALIDARG`, and exactly what an unset `DXC_OUT_PDB` slot
produces.

PR #6834 supplies the missing `SetOutputObject(DXC_OUT_PDB, ...)` call;
it is open/unmerged, consistent with the bug still being present on
ground truth.

## Why a raw COM harness, not a `dxc`/`dxl` command line

`tools/clang/tools/dxclib/dxc.cpp`'s `DxcContext::Link()` -- the code
behind both the `dxc -link` and `dxl.exe` command-line entry points --
only ever calls `GetStatus`/`GetResult`/`GetErrorBuffer` on the linker's
`IDxcOperationResult`. It never `QueryInterface`s for `IDxcResult` and
never calls `GetOutput(DXC_OUT_PDB, ...)`. There is no combination of
CLI flags that can observe this defect; the reporter's own repro steps
are already raw-COM-API steps (`QueryInterface` + `GetOutput`), not a
command line. Per SKILL.md's guidance for symptoms `dxc.exe` cannot
reach, the harness itself is registered as a compiler
(`main-debug-pdb5721`, `run-pdb5721.cmd` -> `pdb5721.py` ->
`pdb5721-harness.cpp`), so `run`/`--shader`/`--expect`/`audit` all work
normally instead of relying on a one-off script.

## Ground truth verification (no rebuild)

The repo working tree's `HEAD` is not the ground-truth commit, but:
- `git merge-base --is-ancestor 89e2f98e2 HEAD` succeeds (it is an
  ancestor).
- `git diff --name-only 89e2f98e2 -- tools/clang/tools/dxcompiler/dxclinker.cpp
  tools/clang/tools/dxcompiler/dxcapi.cpp tools/clang/tools/dxclib/dxc.cpp`
  is empty -- the linker source in the working tree is byte-identical to
  ground truth for every file this bug touches.
- The already-registered `main-debug` compiler
  (`.cache/compilers/main-debug.json`) records `git_commit:
  89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, and its `dxc.exe --version`
  string matches exactly.

So the existing Debug build (and the `dxcompiler.lib`/`.dll` the harness
links/loads) is provably the ground-truth binary for the files this bug
lives in, without rebuilding anything.

## Harness methodology (`pdb5721-harness.cpp`, via `pdb5721.py`)

1. Compile `repro.hlsl` (a `[shader("compute")]` `main` entry -- the
   `[shader(...)]` attribute is required for a `lib_6_x` compile so
   `IDxcLinker::Link` can find the entry point by name; discovered by
   comparing against `tools/clang/test/CodeGenHLSL/lib_cs_entry.hlsl`) to
   `lib_6_3` with `-Zi`.
2. Register it with `IDxcLinker`, then `Link("main", "cs_6_3",
   {-Zi,-Qstrip_debug})`.
3. `QueryInterface` the link result to `IDxcResult`.
4. Report `HasOutput(DXC_OUT_PDB)` and `GetOutput(DXC_OUT_PDB, ...)`.
5. **Anti-vacuity self-test**: on the *same* linked `IDxcResult`, call
   `GetOutput(DXC_OUT_OBJECT, ...)` -- this must succeed, proving the
   QueryInterface/GetOutput plumbing works fine on this exact object and
   isolating the absence to `DXC_OUT_PDB` specifically (not a broken
   harness or failed link).
6. **Positive control**: compile the identical source directly to
   `cs_6_3` (no linker) with the identical `-Zi -Qstrip_debug` flags, and
   confirm `HasOutput(DXC_OUT_PDB)`/`GetOutput` *do* succeed there --
   isolating the defect to the linker code path, not the flags or the
   shader.

Captured in `out-main-debug-pdb5721.txt` (primary):
- `HasOutput(DXC_OUT_PDB) on linked result = FALSE`
- `GetOutput(DXC_OUT_PDB) on linked result = 0x80070057 (E_INVALIDARG)`
- self-test: `GetOutput(DXC_OUT_OBJECT) on linked result = 0x00000000 (S_OK)`,
  2668-byte object -- proves the plumbing works on this object.
- control: direct `Compile(cs_6_3 -Zi -Qstrip_debug)` gets a real PDB
  (`HasOutput` TRUE, `GetOutput` S_OK, 6144 bytes) -- proves the defect is
  linker-specific, not a flag or shader issue.

This reproduces the reporter's exact claim (`E_INVALIDARG` from
`GetOutput(DXC_OUT_PDB, ...)` on a linked result) mechanically, with both
a self-test and a control ruling out the two most likely "it's not really
the bug" explanations (broken harness plumbing; wrong flags/shader).

## Negative control (`control-badentry.hlsl`)

Same shader shape but entry renamed to `notmain`; the harness's hardcoded
`Link("main", ...)` then fails early ("Cannot find definition of function
main") before reaching any of the `HasOutput`/`GetOutput`/self-test
lines. Captured in `variant-badentry-main-debug-pdb5721.txt`, scored
`no-match` against `match.json` as expected (`--expect no-match`) --
confirms the predicate isn't satisfied by an unrelated early failure, only
by the actual documented absence.

## History

Never implemented for this output kind (PR #5678 added the sibling
outputs but skipped PDB; a bare TODO comment marks the gap) -- there is no
"used to work, now broken" boundary to bisect. Classified `history:
always-repro'd`.

## Godbolt

Skipped. Compiler Explorer runs one `dxc` invocation per pane and exposes
no `dxl`/linker equivalent, and even the CLI (`dxc -link`) cannot reach
this code path (see above) -- Godbolt could not distinguish this bug from
"no linker available" regardless.

## Verdict

Reproduces on ground truth `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.
`status: repros`, `suggested_action: still-valid-keep-open` (a fix already
exists as an open, unmerged PR -- #6834 -- so the issue should stay open
pending that PR, not be treated as needing fresh reporter/maintainer
attention). `confidence: high` (mechanical repro + self-test + control,
root cause located in source, matching open fix PR).
