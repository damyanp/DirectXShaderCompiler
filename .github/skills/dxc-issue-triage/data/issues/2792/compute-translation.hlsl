// Compute translation of #2792's repro, for a Compiler Explorer pane that
// hlsl_clang_trunk can actually lower (its DXIL backend cannot lower any pixel
// shader writing SV_Target). Same construction: the root signature reserves
// one 32-bit constant at b0, the cbuffer bound there declares two floats, and
// the shader reads the second one.
cbuffer cb : register(b0)
{
  float a;
  float b;
}

RWBuffer<float> out0 : register(u0);

[RootSignature("RootFlags(0), RootConstants(b0, num32BitConstants = 1), DescriptorTable(UAV(u0))")]
[numthreads(1, 1, 1)]
void main() {
  out0[0] = b;
}
