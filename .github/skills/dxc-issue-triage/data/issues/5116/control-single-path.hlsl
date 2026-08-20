// Negative control for #5116's asymmetry predicate.
//
// Same resource shapes (Texture2D array, SamplerState, RWTexture2D UAV) and the same
// NonUniformResourceIndex + SampleGrad call as the repro, but the array index is computed
// directly with no `inout` copy-out and no multi-path branch ambiguity feeding the resource
// selection. This shader is legal and unambiguous under either shader model, so it must not
// trigger the "local resource not guaranteed to map to unique global resource" diagnostic at
// -T cs_6_5, and it must still emit the SampleGrad DXIL call cleanly at -T cs_6_6. If both
// hold, the repro's #5116 predicate (SM 6.5 diagnoses it / SM 6.6 silently accepts it) must
// score no-match here, proving the predicate is not simply "any SampleGrad-using shader
// compiles cleanly at 6.6" but specifically the SM 6.5/SM 6.6 disagreement on this shader.

Texture2D _allTextures[128];
SamplerState anisoSampler;
RWTexture2D<float4> v;

[numthreads(1,1,1)]
void main(int2 i : SV_DispatchThreadID) {
    Texture2D tex2d = _allTextures[NonUniformResourceIndex(i.x & 127)];
    float4 t = tex2d.SampleGrad(anisoSampler, 0.xx, 0.xx, 0.xx);
    v[i] = t;
}
