// Transformation control for #2792's compute translation. SKILL step 7: when a
// repro is restated to fit Compiler Explorer, run the transformation on a
// known-good case and confirm it still passes -- otherwise the transformation
// is what is being measured, not the issue.
//
// This is compute-translation.hlsl with the out-of-bounds read removed: the
// shader reads only the first 32-bit constant, which is the one the root
// signature reserves. Nothing is out of bounds, so match.json must NOT fire.
cbuffer cb : register(b0)
{
  float a;
  float b;
}

RWBuffer<float> out0 : register(u0);

[RootSignature("RootFlags(0), RootConstants(b0, num32BitConstants = 1), DescriptorTable(UAV(u0))")]
[numthreads(1, 1, 1)]
void main() {
  out0[0] = a;
}
