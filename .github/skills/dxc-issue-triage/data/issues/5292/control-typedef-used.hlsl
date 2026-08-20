struct VSOutput { };
struct PSOutput {};
typedef PSOutput PSPointOutput;

float4 ps_main(VSOutput psIn) {
  PSPointOutput unused_local;
  return float4(0.f, 0.f, 0.f, 1.f);
}
