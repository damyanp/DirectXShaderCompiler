// Control: does NOT read the InputPatch at all, so it should compile to a
// control-point function with zero dx.op.loadInput calls. This proves
// match.json's primary clause discriminates -- it must NOT fire on a
// control-point body that performs no per-component copy, only on one that
// does (as the real repro does).
struct HSInputOutput { float4 pos : POSITION; };

struct HSPerPatchData {
  float edges[3] : SV_TessFactor;
  float inside : SV_InsideTessFactor;
};

[domain("tri")] [partitioning("integer")] [outputtopology("triangle_cw")]
[outputcontrolpoints(3)] [patchconstantfunc("MyPatchConstantFunc")]
HSInputOutput MyHSMainPassthrough(InputPatch<HSInputOutput, 3> input,
                                  uint id : SV_OutputControlPointID) {
  HSInputOutput o;
  o.pos = float4(0, 0, 0, 0);
  return o;
}

void MyPatchConstantFunc(out HSPerPatchData output) {
  output.edges[0] = 1;
  output.edges[1] = 2;
  output.edges[2] = 3;
  output.inside = 4;
}
