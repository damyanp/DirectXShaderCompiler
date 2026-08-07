// Negative control for #2792: fully correct — the root constant block holds
// exactly the one 32-bit constant the cbuffer declares, and the shader reads
// only that constant. Nothing is out of bounds, so match.json must NOT fire.
cbuffer cb : register(b0)
{
  float a;
}

[RootSignature("RootFlags(0), RootConstants(b0, num32BitConstants = 1)")]
float main() : SV_Target {
  return a;
}
