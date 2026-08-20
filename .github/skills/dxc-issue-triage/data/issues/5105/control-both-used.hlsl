// Control for #5105: identical declarations to repro.hlsl, but this time both
// textures are actually referenced. If the predicate's absence clause is
// meaningful (rather than a broken reader that always reports "not_contains
// unusedTex"), then a shader that genuinely uses unusedTex must show it in the
// Resource Bindings table, and the predicate must NOT fire (--expect no-match).
Texture2D<float4> usedTex : register(t0);
Texture2D<float4> unusedTex : register(t1);
SamplerState samp : register(s0);

float4 main(float2 uv : TEXCOORD) : SV_Target
{
    return usedTex.Sample(samp, uv) + unusedTex.Sample(samp, uv);
}
