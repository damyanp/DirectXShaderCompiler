struct ControlPoint {
  float4 position[100] : POSITION;
};

struct HullPatchOut {
    float edge [3] : SV_TessFactor;
    float inside : SV_InsideTessFactor;
};

HullPatchOut HullConst () {
  return (HullPatchOut)0;
}

[domain("tri")]
[partitioning("fractional_odd")]
[outputtopology("triangle_cw")]
[patchconstantfunc("HullConst")]
[outputcontrolpoints(3)]
ControlPoint Hull(InputPatch<ControlPoint, 1> v,
                  uint id : SV_OutputControlPointID) {
  ControlPoint p;
  return p;
}
