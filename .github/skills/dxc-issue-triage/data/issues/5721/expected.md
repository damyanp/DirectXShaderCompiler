# Expected symptom (written before running anything)

Issue: https://github.com/microsoft/DirectXShaderCompiler/issues/5721

Repro quality: **complete**. The issue gives an exact API call sequence:
pass `-Zi` and `-Qstrip_debug` to `IDxcLinker::Link`, `QueryInterface` the
resulting `IDxcOperationResult` for `IDxcResult`, and call
`GetOutput(DXC_OUT_PDB, ...)` on it.

## What "this reproduces" means

1. Compile an HLSL library (`-T lib_6_x`) and register it with `IDxcLinker`.
2. Call `IDxcLinker::Link(entry, targetProfile, libNames, ..., args, ...,
   &ppResult)` with `-Zi -Qstrip_debug` among `args`, where `ppResult` is
   declared as `IDxcOperationResult*` per the `IDxcLinker::Link` signature.
3. `QueryInterface` `ppResult` for `IDxcResult` (the linker's result object
   is documented/expected to support the newer interface, same as
   `IDxcCompiler3::Compile`'s result).
4. Call `GetOutput(DXC_OUT_PDB, IID_PPV_ARGS(&pdbBlob), &pdbName)` on it.

Reproduces == step 4 returns `E_INVALIDARG` (equivalently,
`HasOutput(DXC_OUT_PDB)` returns `FALSE`) for a link whose arguments
requested debug info be split out (`-Zi -Qstrip_debug`), i.e. the linker's
result object never carries a `DXC_OUT_PDB` output at all, unlike an
ordinary (non-linked) `IDxcCompiler3::Compile` with the same flags, which
does.

## Hazard noted before probing

`dxc.exe`'s own `-link` CLI driver (`DxcContext::Link()` in
`tools/clang/tools/dxclib/dxc.cpp`) only ever calls `GetStatus`,
`GetResult` and `GetErrorBuffer` on the linker's `IDxcOperationResult` --
it never calls `GetOutput(DXC_OUT_PDB, ...)` and never asks for
`IDxcResult` at all. So this symptom is **not observable through any
`dxc`/`dxl` command line**, regardless of flags passed; it requires a raw
COM harness that calls `IDxcLinker::Link` directly and inspects the result
object's `IDxcResult` surface. `cmd.txt`/`match.json` will therefore be
absent for this issue and a standalone C++ harness will be used instead
(per SKILL.md's guidance for a symptom no compiler driver reaches).

The issue also names PR #5678 as adding some other linker outputs without
adding `DXC_OUT_PDB`. That PR is already merged (it is what introduced
`SetOutputObject(DXC_OUT_REFLECTION/ROOT_SIGNATURE/SHADER_HASH/OBJECT, ...)`
calls in `DxcLinker::Link`), so the prediction is that current `main` still
has no matching `SetOutputObject(DXC_OUT_PDB, ...)` call in
`dxclinker.cpp`, and the harness should reproduce as filed. That is a
prediction to test against the source and the harness output, not a
conclusion recorded in advance of running anything.
