// From https://github.com/microsoft/DirectXShaderCompiler/issues/6001
// RUN: %dxc -T hs_6_0 -E MyHSMainPassthrough %s | FileCheck %s

// CHECK-NOT: @dx.op.loadInput
// CHECK: !dx.entryPoints = !{![[entries:[0-9]+]]}

// Should entry metadata be null?
// CHECK: ![[entries]] = !{null, !"MyHSMainPassthrough",

struct HSInputOutput { float4 pos : POSITION; };

// HSPerPatchData is not defined in the original issue text; reconstructed
// here using the conventional tri-domain patch-constant fields implied by
// [domain("tri")] and by MyPatchConstantFunc's own field references below
// (edges[0], edges[1], edges[2], inside).
struct HSPerPatchData {
  float edges[3] : SV_TessFactor;
  float inside : SV_InsideTessFactor;
};

[domain("tri")] [partitioning("integer")] [outputtopology("triangle_cw")]
[outputcontrolpoints(3)] [patchconstantfunc("MyPatchConstantFunc")]
HSInputOutput MyHSMainPassthrough(InputPatch<HSInputOutput, 3> input,
                                  uint id : SV_OutputControlPointID) {
  return input[id];
}

void MyPatchConstantFunc(out HSPerPatchData output) {
  output.edges[0] = 1;
  output.edges[1] = 2;
  output.edges[2] = 3;
  output.inside = 4;
}
