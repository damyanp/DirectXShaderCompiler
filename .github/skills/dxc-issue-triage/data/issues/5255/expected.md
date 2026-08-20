# Expected symptom (issue #5255)

Tool: `dxr.exe` (the standalone HLSL rewriter, `-remove-unused-functions
-remove-unused-globals -E vs_main`), not `dxc.exe`. `dxr` has no `-T` profile.

Repro shader declares:

- `struct InstanceDataStructType { float4 data; };`
- `cbuffer InstanceData { InstanceDataStructType mData[2]; };` -- used, `vs_main`
  reads `mData[0].data`.
- `struct InstanceDataStructTypeNotUsed { float4 data; };` -- genuinely unused,
  referenced by nothing.
- `cbuffer InstanceDataNotUsed { InstanceDataStructType mDataNotUsed[2]; };` --
  the cbuffer itself is unreferenced by `vs_main`, but its one member reuses
  the *same* `InstanceDataStructType` type (this looks like a copy/paste typo
  in the report -- it names `InstanceDataStructType`, not
  `InstanceDataStructTypeNotUsed` -- but it is what the reporter's shader
  says, so it is kept as filed).

Per `tools/clang/test/HLSLFileCheck/rewriter/remove-unused-globals.hlsl`,
"Unused cbuffers are not removed at this time" -- both `cbuffer` blocks are
expected to remain in the output. `InstanceDataStructTypeNotUsed` (the fully
dead struct) is expected to be removed by `-remove-unused-functions`/`-remove-
unused-globals`, per the existing rewriter test contract for unused types.

**Reproduces** if the rewritten output keeps `cbuffer InstanceData` and/or
`cbuffer InstanceDataNotUsed` referencing `InstanceDataStructType` as a field
type (directly, in `InstanceDataStructType mData[2];`) while the
`struct InstanceDataStructType { ... };` declaration itself has been deleted
from the output -- i.e. the emitted HLSL references an undeclared type and
would fail to recompile. This is the exact defect quoted in the issue body:
"Output's all cbuffer declaration are still remaining, but its referenced
struct definitions are removed."

**Does not reproduce** if `struct InstanceDataStructType { ... };` is present
in the output ahead of both cbuffers that reference it.

Repro quality: **complete** -- the issue body includes the exact input shader
and the exact (malformed) output the reporter observed, plus the exact `dxr`
command line.

Out of scope for this triage: the two follow-up comments asking for a new
feature ("remove cbuffer definitions whose members are all unused") and
offering an unlinked, unmerged patch for it. That is a distinct enhancement
request layered onto this bug report, not the reported defect, and is noted
separately in `notes.md` but not scored by `match.json`.
