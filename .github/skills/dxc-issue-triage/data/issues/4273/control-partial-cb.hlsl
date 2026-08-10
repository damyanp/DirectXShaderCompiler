// Control for #4273: repro.hlsl plus one unused constant INSIDE an otherwise-used cbuffer
// block. Sharpens the description of the carve-out -- the question is whether the rewriter
// leaves individual unused members of an explicit block alone as well as whole unused blocks.
// The whole-block symptom is unchanged here, so match.json must still score `match`; read the
// capture for whether gAUnusedInBlock survived.

cbuffer cbA
{
  float4 gA;
  float4 gAUnusedInBlock;
};

cbuffer cbB
{
  float4 gB;
};

float4 gLooseUnused;
float4 gLooseUsed;

float4 vsMain(float4 pos : POSITION) : SV_Position
{
  return pos * gA + gLooseUsed;
}

float4 psMain() : SV_Target
{
  return gB;
}
