> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#5350](https://github.com/microsoft/DirectXShaderCompiler/issues/5350).

Checked `main` (`89e2f98e2`) for whether either outstanding question is already implemented. Neither is:

- `ID3D12FunctionReflection1` / `GetDesc1` / `D3D12_FUNCTION_DESC1` do not
  exist anywhere in this repository. The current
  `CFunctionReflection::GetDesc(D3D12_FUNCTION_DESC*)` fills only `Version`,
  `ConstantBuffers` and `BoundResources`; it never reads node launch mode or
  node ID.
- The data is already computed internally
  (`DxilFunctionProps::NodeProps.LaunchType`, `NodeShaderID`,
  `include/dxc/DXIL/DxilFunctionProps.h`) and serialized into RDAT for the
  runtime; reflection does not expose it.
- @damyanp's linked PR #6827 ("Added implementation for
  `ID3D12FunctionReflection1::GetDesc1`") is a concrete attempt at question 1.
  It's still open and unreviewed, and per its own description it also needs
  `D3D12_FUNCTION_DESC1` added to DirectX-Headers first.

Since both questions are still open, and there's an existing PR to react to,
suggested action is to have a maintainer weigh in on #6827 rather than
treating this as something a compiler repro could settle either way.

Suggested labels: `enhancement`, `api` (in addition to the existing
`reflection`, `sm6.8`).

---
<sub>Triaged with AI assistance. This is a design question, not something a compiler repro can settle, so the assessment above comes from reading the reflection implementation and `DxilFunctionProps` in the current source rather than from running a shader; please flag anything that looks wrong.</sub>
