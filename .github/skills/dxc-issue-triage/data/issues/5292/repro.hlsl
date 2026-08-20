struct VSOutput { };
struct PSOutput {};
typedef PSOutput PSPointOutput;

float4 ps_main(VSOutput psIn) { return float4(0.f, 0.f, 0.f, 1.f); }
