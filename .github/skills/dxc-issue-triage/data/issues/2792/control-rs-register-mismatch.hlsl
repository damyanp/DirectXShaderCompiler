// Negative control for #2792: the root signature binds b1 while the shader's
// cbuffer is at b0, so the shader's CBV is genuinely not covered by the root
// signature. DXC's root-signature-vs-shader validation is expected to reject
// this, which is what proves that validation actually runs on this command
// line -- so the absence of a *size* diagnostic on repro.hlsl is a real gap
// rather than "no root signature checking happened at all".
// match.json must NOT fire (a diagnostic is emitted and no DXIL is produced).
cbuffer cb : register(b0)
{
  float a;
  float b;
}

[RootSignature("RootFlags(0), RootConstants(b1, num32BitConstants = 4)")]
float main() : SV_Target {
  return b;
}
