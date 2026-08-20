> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5703](https://github.com/microsoft/DirectXShaderCompiler/issues/5703).

Reproduced on current `main` (`89e2f98e2`) and the reported build
(`v1.7.2308`), so this hasn't changed since filing.

The behavior is by design, not a bug: `RDAT` (`DXC_PART_REFLECTION_DATA`)
is written only for library modules
(`lib/DxilContainer/DxilContainerAssembler.cpp`, keyed on
`ShaderModel::IsLib()`). A finalized, non-library container -- which is
what `IDxcLinker::Link(entry, "cs_6_3", ...)` produces -- gets `PSV0`
instead, and never `RDAT` (just like a shader compiled *directly* to
`cs_6_3`). Confirmed both ways:

- library compile: `SFI0, VERS, RDAT(232), STAT, HASH, DXIL`
- linked to `cs_6_3`: `SFI0, ISG1, OSG1, PSV0(132), STAT, ILDN, HASH, DXIL`
- direct compile to `cs_6_3` (no linker involved at all): identical to
  the linked case (no `RDAT`).

The resource-binding information isn't lost -- `dxa
-dumpreflection` (which drives `ID3D12ShaderReflection`, not
`ID3D12LibraryReflection`) on the linked container correctly reports both
`texResource` (`t900`) and `rwTexResource` (`u0`, space2400). `RDAT`
specifically feeds `ID3D12LibraryReflection`, which doesn't apply once a
shader has been finalized to a concrete profile; `ID3D12ShaderReflection`
is the interface to use on a linked/compiled container, and it works.

Suggest dropping `bug` -- `reflection` and `shader-linking` still fit. A
short doc note (or a remark on `IDxcLinker::Link`) stating that a
linked/finalized container never carries `RDAT`, and that
`ID3D12ShaderReflection` is the correct reflection interface post-link,
would clarify this.

(Aside: the literal repro no longer links on current `main` -- `dxl`
reports "Cannot find definition of function main" -- because
`[numthreads]` alone doesn't tag an entry point without an accompanying
`[shader("compute")]`; it did link at v1.7.2308. Adding
`[shader("compute")]` restores it and doesn't change the RDAT finding
above. Flagging this only so it isn't confused with the RDAT question if
this gets revisited.)

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
