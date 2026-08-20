# #5849 expected.md

**Issue type:** design/feature request, not a crash or miscompile. The reporter (a
maintainer, tex3d) describes a real gap and proposes three fixes; a second maintainer
(amarpMSFT) replies "Agreed, option 3 makes sense" one comment later. There is no
attached repro shader; the issue body is entirely prose describing RDAT/runtime
behaviour.

**The three options as literally numbered in the issue body are 1, 3, 5** (the
reporter's own list markup, not a transcription error). The reporter's own closing
line says "So far, (3) zeroing the payload size looks like the best option" --
referring to the conceptually-third bullet (numbered "5." in the raw markdown:
"Set the reported payload size in RDAT to zero for each DXR entry point that uses
PAQs on the payload"). amarpMSFT's "option 3" agreement is read as agreeing with
that same zeroing proposal, since it is the option the reporter had just called out
as "the best option" and the one amarpMSFT's one-line reply immediately follows.

**What "reproduces" means here:** the compiler still gives the runtime no way to
tell whether Payload Access Qualifiers (PAQs) were used on a given DXR
any-hit/closest-hit/miss/callable entry point. Concretely: for a shader that
declares its payload with PAQs (default-enabled on SM 6.7+, i.e. no
`-disable-payload-qualifiers`), the RDAT `RuntimeDataFunctionInfo::PayloadSizeInBytes`
field for that entry point still carries the shader's real payload struct size,
identical to what a non-PAQ (or `-disable-payload-qualifiers`) build would emit --
i.e. nothing in RDAT lets the runtime skip its `MaxPayloadSizeInBytes` validation.

**What "fixed" would look like:** RDAT records `PayloadSizeInBytes == 0` (or some
other explicit indication) for an entry point that used PAQs on SM 6.7+, while a
build compiled with `-disable-payload-qualifiers` (or with PAQs unavailable) still
reports the real size, matching current runtime enforcement semantics for that case.

**Repro quality:** `agent-constructed`. No shader is attached to the issue; a
minimal DXR library using PAQ-qualified fields on a closest-hit/miss payload is
built here to make the RDAT field directly observable.

**Method note:** `dxc.exe`/`dxil-dis` alone cannot answer this -- the field lives
in the `RDAT` container part, produced only at container-assembly time
(`lib/DxilContainer/DxilContainerAssembler.cpp`), not in the LLVM IR/DXIL text a
`-fcgl`/`-Fc` dump shows. `dxa.exe` (which ships a `-dumprdat`/`-dumpreflection`
dumper) is not present in this checkout's Debug build output and this triage run
may not build anything (no rebuild permitted), so the RDAT `FunctionTable` is
parsed directly out of the compiled container in Python, using the on-disk record
layout in `include/dxc/DxilContainer/DxilRuntimeReflection.h` and
`RDAT_LibraryTypes.inl` (`RuntimeDataFunctionInfo`: Name, UnmangledName,
Resources, FunctionDependencies, ShaderKind, PayloadSizeInBytes,
AttributeSizeInBytes, FeatureInfo1/2, ShaderStageFlag, MinShaderTarget -- all
`uint32_t`, so `PayloadSizeInBytes` sits at a fixed byte offset 20 from the start
of every function record regardless of table stride/version). This is a source
citation, not a black-box assumption; both the `RuntimeDataFunctionInfo` field
order and the container header layout are read directly from the two headers
above and cross-checked against a captured `d3dreflect` `CHECK` test's own
`RuntimeDataFunctionInfo` dump.
