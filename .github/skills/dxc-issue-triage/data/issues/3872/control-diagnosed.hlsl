// POSITIVE CONTROL for the missing diagnostic in issue 3872.
// Expect MATCH under match-diag.json, and no-match under match.json.
//
// Same five entry points and the same five command lines as repro.hlsl, so the
// only thing that changes is WHERE SV_ShadingRate sits. Here it sits in three
// cells the same SemanticInterpretation table already marks NA, in the same
// stages:
//
//   VSIn   -- SV_ShadingRate as a vertex shader INPUT parameter
//   PCOut  -- SV_ShadingRate in the hull shader's patch-constant OUTPUT
//   DSIn   -- the same struct read as the domain shader's patch-constant INPUT
//
// If DXC reports these and says nothing about the repro's four positions, the
// silence there is a decision recorded in the table, not a check that never
// ran.

struct VSOutPlain {
  float4 pos : SV_Position;
  float2 uv : TEXCOORD0;
};

struct PatchConstSR {
  float edges[3] : SV_TessFactor;
  float inside : SV_InsideTessFactor;
  uint rate : SV_ShadingRate;
};

VSOutPlain VSMain(float4 pos : POSITION, uint rate : SV_ShadingRate) {
  VSOutPlain o;
  o.pos = pos;
  o.uv = (float2)rate;
  return o;
}

PatchConstSR PCMain(InputPatch<VSOutPlain, 3> ip) {
  PatchConstSR c;
  c.edges[0] = 1;
  c.edges[1] = 1;
  c.edges[2] = 1;
  c.inside = 1;
  c.rate = 1;
  return c;
}

PatchConstSR PCMainRate(InputPatch<VSOutPlain, 3> ip) {
  PatchConstSR c;
  c.edges[0] = 1;
  c.edges[1] = 1;
  c.edges[2] = 1;
  c.inside = 1;
  c.rate = 2;
  return c;
}

[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("PCMainRate")]
VSOutPlain HSCPInMain(InputPatch<VSOutPlain, 3> ip, uint i : SV_OutputControlPointID) {
  VSOutPlain o;
  o.pos = ip[i].pos;
  o.uv = ip[i].uv;
  return o;
}

[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("PCMain")]
VSOutPlain HSCPOutMain(InputPatch<VSOutPlain, 3> ip, uint i : SV_OutputControlPointID) {
  VSOutPlain o;
  o.pos = ip[i].pos;
  o.uv = ip[i].uv;
  return o;
}

[domain("tri")]
VSOutPlain DSCPInMain(PatchConstSR pc, float3 bary : SV_DomainLocation,
                      const OutputPatch<VSOutPlain, 3> patch) {
  VSOutPlain o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.uv = (float2)pc.rate;
  return o;
}

[domain("tri")]
VSOutPlain DSOutMain(PatchConstSR pc, float3 bary : SV_DomainLocation,
                     const OutputPatch<VSOutPlain, 3> patch) {
  VSOutPlain o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.uv = (float2)pc.rate;
  return o;
}
