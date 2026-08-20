> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5169](https://github.com/microsoft/DirectXShaderCompiler/issues/5169).

Still open and still accurate, checked against `main` at
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.

The vendored `external/DirectX-Headers` submodule (pinned at
`980971e83587...`) still declares `D3D_SHADER_VARIABLE_CLASS` with members
`D3D_SVC_SCALAR` through `D3D_SVC_INTERFACE_POINTER` only — no
`D3D_SVC_BIT_FIELD`. DXC's own source still works around exactly that, in
both `lib/HLSL/DxilContainerReflection.cpp` and
`lib/DxilContainer/D3DReflectionStrings.cpp`:

```c
// FIXME: remove the define once D3D_SVC_BIT_FIELD added into
// D3D_SHADER_VARIABLE_CLASS.
#define D3D_SVC_BIT_FIELD                                                      \
  ((D3D_SHADER_VARIABLE_CLASS)(D3D_SVC_INTERFACE_POINTER + 1))
```

`git log --all -S "D3D_SVC_BIT_FIELD"` lists three commits touching these
files; only #5142 (which added the workaround) writes new text, and the
other two are file moves that carry it forward unchanged. The gap this issue
tracks has been open since #5142 merged on 2023-05-05.

This isn't something a shader compile can show either way — DXC already
supplies the value itself regardless of the header, so behavior is identical
before and after the header is fixed. The remaining work is exactly what the
issue says: add `D3D_SVC_BIT_FIELD` to the real `D3D_SHADER_VARIABLE_CLASS`
enum, then drop the `#define ADD_SVC_BIT_FIELD` workaround (and its FIXME) in
both files above.

Current labels (`bug`, `hlsl2021`, `reflection`) still fit; no changes
suggested.

---
<sub>Triaged with AI assistance. Findings were verified by reading the cited
source files directly; please flag anything that looks wrong.</sub>
