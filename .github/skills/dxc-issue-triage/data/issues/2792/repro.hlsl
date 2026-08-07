cbuffer cb : register(b0)
{
  float a;
  float b;
}

[RootSignature("RootFlags(0), RootConstants(b0, num32BitConstants = 1)")]
float main() : SV_Target {
  return b;
}
