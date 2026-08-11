// Issue 4615 control-diag: identical physical layout to repro.hlsl, but the
// statement after the #line directive does not compile. Scores no-match under
Texture2D<float4> g_tex : register(t0);
SamplerState g_smp : register(s0);
// match.json (no DXIL is produced); what it is for is the diagnostic text.
float4 main(float2 uv : TEXCOORD0) : SV_Target {
  float4 before = g_tex.Sample(g_smp, uv);
#line 400 "virtual-source.hlsl"
  return before.no_such_member;
}
