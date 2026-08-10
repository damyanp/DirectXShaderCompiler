// POSITIVE CONTROL for match-validator.json (issue 3872).
// Expect MATCH: DXIL validation must reject this, under the repro's own five
// command lines.
//
// Same five entry points as repro.hlsl and no SV_ShadingRate anywhere. The one
// difference is a deliberately incompatible root signature: the shaders read a
// Texture1D at t3 while the attached root signature only describes t0, which
// the DXIL validator rejects with
//   error: validation errors
//   ...Root Signature in DXIL container is not compatible with shader...
// (the same failure tools/clang/test/DXILValidation/rootSigDefine10.hlsl
// checks for). Without this control, "match-validator.json did not fire on the
// repro" would be indistinguishable from "validation never ran".

#define RS "DescriptorTable(SRV(t0))"

Texture1D<float> tex : register(t3);

struct VSOutPlain {
  float4 pos : SV_Position;
  float2 uv : TEXCOORD0;
};

struct PatchConst {
  float edges[3] : SV_TessFactor;
  float inside : SV_InsideTessFactor;
};

[RootSignature(RS)]
VSOutPlain VSMain(float4 pos : POSITION, uint rate : RATE) {
  VSOutPlain o;
  o.pos = pos;
  o.uv = (float2)(tex[rate] + (float)rate);
  return o;
}

PatchConst PCMain(InputPatch<VSOutPlain, 3> ip) {
  PatchConst c;
  c.edges[0] = 1;
  c.edges[1] = 1;
  c.edges[2] = 1;
  c.inside = 1;
  return c;
}

PatchConst PCMainRate(InputPatch<VSOutPlain, 3> ip) {
  PatchConst c;
  c.edges[0] = 1;
  c.edges[1] = 1;
  c.edges[2] = 1;
  c.inside = 1;
  return c;
}

[RootSignature(RS)]
[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("PCMainRate")]
VSOutPlain HSCPInMain(InputPatch<VSOutPlain, 3> ip, uint i : SV_OutputControlPointID) {
  VSOutPlain o;
  o.pos = ip[i].pos;
  o.uv = ip[i].uv + tex[i];
  return o;
}

[RootSignature(RS)]
[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("PCMain")]
VSOutPlain HSCPOutMain(InputPatch<VSOutPlain, 3> ip, uint i : SV_OutputControlPointID) {
  VSOutPlain o;
  o.pos = ip[i].pos;
  o.uv = ip[i].uv + tex[i];
  return o;
}

[RootSignature(RS)]
[domain("tri")]
VSOutPlain DSCPInMain(PatchConst pc, float3 bary : SV_DomainLocation,
                      const OutputPatch<VSOutPlain, 3> patch) {
  VSOutPlain o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.uv = patch[0].uv + tex[0];
  return o;
}

[RootSignature(RS)]
[domain("tri")]
VSOutPlain DSOutMain(PatchConst pc, float3 bary : SV_DomainLocation,
                     const OutputPatch<VSOutPlain, 3> patch) {
  VSOutPlain o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.uv = patch[0].uv + tex[0];
  return o;
}
