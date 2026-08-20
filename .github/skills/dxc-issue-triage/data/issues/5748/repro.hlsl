RWStructuredBuffer<float4> output;
groupshared  float4 gs;
struct PosStruct {
  float4 pos : SV_Position;
};

struct PCStruct
{
  float Edges[3]  : SV_TessFactor;
  float Inside : SV_InsideTessFactor;
};

[shader("hull")]
[domain("tri")]
[partitioning("fractional_odd")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("HSPatch")]
PosStruct main(InputPatch<PosStruct, 3> p,
                 uint ix : SV_OutputControlPointID)
{
  PosStruct s;
  s.pos = p[ix].pos;
  return s;
}

PCStruct HSPatch(InputPatch<PosStruct, 3> ip,
                 OutputPatch<PosStruct, 3> op,
                 uint ix : SV_PrimitiveID)
{
  PCStruct a;
  a.Edges[0] = gs.x;
  a.Edges[1] = gs.y;
  a.Edges[2] = gs.z;
  a.Inside = gs.w;
  return a;
}
