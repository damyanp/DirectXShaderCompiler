// #5105: an unused, explicitly-registered resource should remain visible in
// reflection/disassembly even though nothing in the entry point references it.
//
// unusedTex (t1) is declared but never read. usedTex (t0) and samp (s0) are
// both read, so they must survive under any configuration; unusedTex is the
// resource under test.
Texture2D<float4> usedTex : register(t0);
Texture2D<float4> unusedTex : register(t1);
SamplerState samp : register(s0);

float4 main(float2 uv : TEXCOORD) : SV_Target
{
    return usedTex.Sample(samp, uv);
}
