struct VSOutput { };
struct PSOutput {};
typedef PSOutput PSPointOutput;

float4 ps_main(VSOutput psIn) : SV_Target { return float4(0.f, 0.f, 0.f, 1.f); }
