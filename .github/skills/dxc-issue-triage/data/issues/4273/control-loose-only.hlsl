// Negative control for #4273's predicate.
// Identical to repro.hlsl except that cbB's constant is a LOOSE global instead of living in
// an explicit cbuffer block. There is no `cbuffer cbB` here, so clause 1 of match.json must
// fail and the predicate must score no-match -- which is what proves clause 1 discriminates
// rather than matching everything.
// It doubles as the contrast tex3d describes: gLooseUnusedB is exactly the kind of constant
// -remove-unused-globals does drop.

cbuffer cbA
{
  float4 gA;
};

float4 gLooseUnusedB;
float4 gLooseUnused;
float4 gLooseUsed;

float4 vsMain(float4 pos : POSITION) : SV_Position
{
  return pos * gA + gLooseUsed;
}

float4 psMain() : SV_Target
{
  return gLooseUnusedB;
}
