// Issue 4615 control-echo: the #line text below sits inside a comment, so the
// preprocessor never acts on it -- but -Zi still echoes the whole source into
Texture2D<float4> g_tex : register(t0);
SamplerState g_smp : register(s0);
// !dx.source.contents. Physical layout is identical to repro.hlsl.
float4 main(float2 uv : TEXCOORD0) : SV_Target {
  float4 before = g_tex.Sample(g_smp, uv);
// #line 400 "virtual-source.hlsl"
  return before * 2.0f;
}
