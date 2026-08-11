// Issue 4666 -- POSITIVE CONTROL, run on every probed release.
//
// Identical to repro.hlsl except for the struct declaration below, which is
// never referenced. The issue body states that merely having this declaration
// ahead of the function makes the unchanged `SamplerState Samplers[2]`
// parameter compile.
//
// This is the control that decides whether a release is valid evidence:
//
//   control clean + repro errors -> that release exhibits the reported defect
//   control errors too           -> that release does not support sampler-array
//                                   parameters in ANY form, so its error is not
//                                   the reported defect and the release is not
//                                   evidence
//
// Without it, a release predating sampler-array parameters emits its own error
// and scores as a textbook reproduction, because the reported symptom IS a
// diagnostic and `classify`'s feature-absence markers do not cover this one.
//
// Expected: no-match (compiles clean).
struct Resources
{
    SamplerState Samplers[2];
};

void Reflection(Texture2D<float4> Textures[4], SamplerState Samplers[2]) {}

float4 main() : SV_Target
{
    return 0;
}
