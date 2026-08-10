// Agent-constructed from the reporter's prose in issue 4273:
//   "cbA, cbB, vsMain, psMain wrote in the same file. vsMain used cbA. psMain used cbB.
//    When I rewirte the entry "vsMain" . I expected the result code just remain cbA."
// gLooseUnused / gLooseUsed are the $Globals contrast tex3d describes: constants outside an
// explicit block. They are the self-test that -remove-unused-globals was honoured.

cbuffer cbA
{
  float4 gA;
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
