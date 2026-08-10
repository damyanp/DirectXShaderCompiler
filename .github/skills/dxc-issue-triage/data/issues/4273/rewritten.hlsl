cbuffer cbA {
  const float4 gA;
}
;
cbuffer cbB {
  const float4 gB;
}
;
const float4 gLooseUsed;
float4 vsMain(float4 pos : POSITION) : SV_Position {
  return pos * gA + gLooseUsed;
}



