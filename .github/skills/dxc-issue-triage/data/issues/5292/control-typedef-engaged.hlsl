struct VSOutput { };
struct PSOutput {};
typedef PSOutput PSPointOutput;

static PSPointOutput g_dummy;

float4 ps_main(VSOutput psIn) {
  PSPointOutput local = g_dummy;
  (void)local;
  return float4(0.f, 0.f, 0.f, 1.f);
}
