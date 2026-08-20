> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5721](https://github.com/microsoft/DirectXShaderCompiler/issues/5721).

Reproduced on current `main` (`89e2f98e2`).

Confirmed with a small COM harness that drives `IDxcLinker::Link` and
`IDxcResult` directly (this can't be seen from a `dxc`/`dxl` command
line -- the CLI's link path never asks for `DXC_OUT_PDB` either):

- `Link("main", "cs_6_3", {-Zi,-Qstrip_debug})` succeeds.
- On the linked `IDxcResult`: `HasOutput(DXC_OUT_PDB)` is `FALSE`, and
  `GetOutput(DXC_OUT_PDB, ...)` returns `E_INVALIDARG` -- exactly the
  reported behavior.
- Self-test on the same result object: `GetOutput(DXC_OUT_OBJECT, ...)`
  succeeds, so the plumbing isn't broken -- `DXC_OUT_PDB` specifically was
  never populated.
- Control: compiling the identical source directly to `cs_6_3` with the
  identical `-Zi -Qstrip_debug` flags (no linker) *does* produce a PDB --
  isolates the gap to the linker path.

Root cause: `tools/clang/tools/dxcompiler/dxclinker.cpp`'s `Link()`
builds `DXC_OUT_OBJECT`/`DXC_OUT_ROOT_SIGNATURE`/`DXC_OUT_SHADER_HASH`/
`DXC_OUT_REFLECTION` outputs (added by
[#5678](https://github.com/microsoft/DirectXShaderCompiler/pull/5678))
immediately followed by a bare `// TODO: DFCC_ShaderDebugName` comment --
`DXC_OUT_PDB` was never wired up alongside those. `IDxcResult::GetOutput`
returns `E_INVALIDARG` for any output slot that was never
`SetOutputObject`'d, which is exactly what happens here.

There's already an open PR for this:
[#6834](https://github.com/microsoft/DirectXShaderCompiler/pull/6834)
("Add PDB output to linker") adds the missing `SetOutputObject` call and
says it fixes this issue; it just hasn't merged yet. Suggest keeping this
open until that lands rather than treating it as needing fresh
repro/triage.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
