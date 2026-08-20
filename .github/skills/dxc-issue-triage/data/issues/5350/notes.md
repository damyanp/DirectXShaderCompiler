# Issue #5350 -- notes

## What the issue asks

Filed 2023-06-28 by llvm-beanz (DXC/Clang maintainer), not as a bug but as two
open design questions about `ID3D12LibraryReflection` / node-shader
reflection:

1. Extend the existing library/function reflection COM interfaces so a caller
   can retrieve, per node-shader entry point, the RDAT properties that
   describe a Work Graph node -- specifically its launch mode (broadcasting /
   coalescing / thread) and its node ID (name + array index), so an
   application can set up per-launch-mode or per-node overrides.
2. Or design a more general, future-proof reflection API that surfaces RDAT
   more directly instead of growing the COM surface incrementally.

The only comment (damyanp, MEMBER, 2024-09-12) links a related PR and states
the maintainers' direction: "Related: #6827. Current thinking is that we'll
likely consider this as we bring up reflection for DXIL in clang."

## What is checkable

There is no shader input/output pair that could show "reproduces" or "fixed"
for a design question. What can be checked mechanically is whether the
described capability -- node launch mode / node ID via the public reflection
API -- exists in `main` today.

### Source inspection (main-debug, `89e2f98e2`)

- `git grep -c "FunctionReflection1"` across the tracked tree returns **zero**
  matches: `ID3D12FunctionReflection1` / `GetDesc1` / `D3D12_FUNCTION_DESC1`
  do not exist anywhere in this repository, public headers included.
- The only `GetDesc` implementation for a per-function reflection object is
  `CFunctionReflection::GetDesc(D3D12_FUNCTION_DESC *pDesc)`
  (`lib/HLSL/DxilContainerReflection.cpp:2838`). Reading the full body
  (lines 2838-2868+) shows it fills `Version`, `ConstantBuffers`,
  `BoundResources` and leaves several fields explicitly commented `// Unset:`;
  none of the code touches node launch mode, node ID, or any `Node*` field.
- The node-shader properties the issue is asking to expose already exist
  *internally*: `DxilFunctionProps::NodeProps` (`LaunchType`, `IsProgramEntry`,
  `DispatchGrid`, `MaxDispatchGrid`, `MaxRecursionDepth`) and
  `NodeID NodeShaderID` / `NodeID NodeShaderSharedInput`
  (`include/dxc/DXIL/DxilFunctionProps.h:182-193`). They are computed at
  compile time and serialized into the RDAT container for the runtime, but
  `CFunctionReflection` never reads `m_pProps->Node` or `m_pProps->NodeShaderID`.
- `lib/DxilContainer/D3DReflectionDumper.cpp` (the reflection-dumping test
  helper used by `dxa -dumpreflection`) contains no reference to "Node" either
  -- confirming the gap is in the data actually surfaced, not merely in one
  dumper.

This is the "inspect the public interface table and all emitters" step this
skill recommends for a capability-absence claim; a single compiled shader
would be weaker evidence than reading the COM implementation directly, and
there is no second, contrasting compiler that implements Work Graph node
reflection to compare against.

### Related PR (context, not evidence of a fix)

PR #6827, "Added implementation for ID3D12FunctionReflection1::GetDesc1",
opened 2024-07-25, is **still open and unmerged** as of this triage (last
updated 2025-11-07). Its own description says it depends on
`DirectX-Headers#135` to define `D3D12_FUNCTION_DESC1`, i.e. even the header
side of question 1 is not yet in place. This corroborates the source
inspection: nothing in this area has landed on `main`, and the PR is exactly
an attempt at question 1, still pending maintainer review two years after
filing.

## Verdict

`not-compiler-verifiable` -- this is an API/interface design question with
two explicit "outstanding questions" the reporter (a maintainer) posed to the
team, not a compiler defect. No `cmd.txt`/`match.json` is created: there is no
dxc invocation whose pass/fail state could answer either question, and
manufacturing one would misrepresent a design discussion as a measured
regression. The one fact this triage *can* state is that the capability
described does not exist on `main` today and the one PR attempting part of it
is still open -- i.e. both outstanding questions remain unresolved. Compiler
Explorer is skipped for the same reason (`godbolt_skip` in `verdict.json`):
there is no shader whose compilation would demonstrate more or less
reflection-API surface.

Suggested action: `needs-human-judgement` (an API design decision belongs to
the maintainers, and PR #6827 is the concrete artifact already awaiting
their review).
