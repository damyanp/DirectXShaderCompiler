# Expected symptom (written before running anything)

Issue: https://github.com/microsoft/DirectXShaderCompiler/issues/5703

Repro quality: **complete**. The issue body gives a full C++ repro using
`IDxcCompiler3::Compile`, `IDxcLinker::RegisterLibrary` + `Link`, and
`IDxcContainerReflection` to enumerate container parts. The HLSL source and
exact API call sequence are both given verbatim.

## What "this reproduces" means

1. Compile the given HLSL source as a library (`-T lib_6_3`).
2. Link it to a compute shader (`Link(L"main", L"cs_6_3", ...)`).
3. Load the linked container with `IDxcContainerReflection` and enumerate
   part kinds via `GetPartKind`.
4. The reporter asserts this should find a part with kind
   `DXC_PART_REFLECTION_DATA` (FourCC `RDAT`) and says the assert fails --
   i.e. **no RDAT part is present in the linked container**.

Reproduces == the linked (post-`Link`, target profile `cs_6_3`) container's
part table contains no `RDAT` part.

## Hazard noted before probing

`lib/DxilContainer/DxilContainerAssembler.cpp` writes the `RDAT` part only
inside the `pSM->IsLib()` branch of `WriteProgramPart`/container assembly;
the non-library branch (which is what a `Link(..., "cs_6_3", ...)` call
produces) writes `PSV0` instead, unconditionally, with no `RDAT` part at
all -- for *any* non-library container, not only linked ones. This predicts
the reported "actual behavior" is the container format working as designed
for a finalized (non-library) shader target, not a linker-specific defect.
That is a prediction to test, not a conclusion: it will be checked directly
against a compiled container's part table, and against a control that
skips the linker entirely (direct `-T cs_6_3` compile) to see whether the
same absence occurs with no linking involved at all.
