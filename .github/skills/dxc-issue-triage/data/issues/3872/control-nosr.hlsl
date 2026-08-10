// NEGATIVE CONTROL for issue 3872, expect no-match under match.json and under
// match-validator.json.
//
// Byte-for-byte the same five-entry-point VS/HS/DS pipeline as repro.hlsl with
// exactly one difference: every `SV_ShadingRate` is an arbitrary `RATE`
// semantic instead. It compiles cleanly on all five command lines, so a
// predicate that still matched here would be measuring "a shader compiled",
// not "SV_ShadingRate was accepted in these signature positions".

struct VSOutRate {
  float4 pos : SV_Position;
  uint rate : RATE;
};

struct VSOutPlain {
  float4 pos : SV_Position;
  float2 uv : TEXCOORD0;
};

struct PatchConst {
  float edges[3] : SV_TessFactor;
  float inside : SV_InsideTessFactor;
};

VSOutRate VSMain(float4 pos : POSITION, uint rate : RATE) {
  VSOutRate o;
  o.pos = pos;
  o.rate = rate;
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

PatchConst PCMainRate(InputPatch<VSOutRate, 3> ip) {
  PatchConst c;
  c.edges[0] = 1;
  c.edges[1] = 1;
  c.edges[2] = 1;
  c.inside = 1;
  return c;
}

[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("PCMainRate")]
VSOutPlain HSCPInMain(InputPatch<VSOutRate, 3> ip, uint i : SV_OutputControlPointID) {
  VSOutPlain o;
  o.pos = ip[i].pos;
  o.uv = (float2)ip[i].rate;
  return o;
}

[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("PCMain")]
VSOutRate HSCPOutMain(InputPatch<VSOutPlain, 3> ip, uint i : SV_OutputControlPointID) {
  VSOutRate o;
  o.pos = ip[i].pos;
  o.rate = (uint)ip[i].uv.x;
  return o;
}

[domain("tri")]
VSOutPlain DSCPInMain(PatchConst pc, float3 bary : SV_DomainLocation,
                      const OutputPatch<VSOutRate, 3> patch) {
  VSOutPlain o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.uv = (float2)patch[0].rate;
  return o;
}

[domain("tri")]
VSOutRate DSOutMain(PatchConst pc, float3 bary : SV_DomainLocation,
                    const OutputPatch<VSOutPlain, 3> patch) {
  VSOutRate o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.rate = (uint)patch[0].uv.x;
  return o;
}
