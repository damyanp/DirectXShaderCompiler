// Issue 3872: SV_ShadingRate accepted in HS/DS control-point signatures.
//
// One file, five entry points, five compiles (see cmd.txt). Each compile puts
// SV_ShadingRate in exactly ONE signature position, so each `$ dxc ...` block
// in the capture isolates one row of the SemanticInterpretation table:
//
//   VSMain        vs_6_4  VSOut    <- SELF-TEST: the position the spec permits
//   HSCPInMain    hs_6_4  HSCPIn   <- disputed
//   HSCPOutMain   hs_6_4  HSCPOut  <- disputed
//   DSCPInMain    ds_6_4  DSCPIn   <- disputed
//   DSOutMain     ds_6_4  DSOut    <- disputed
//
// 6_4 is the oldest shader model that can express SV_ShadingRate at all: the
// interpretation table gates every ShadingRate entry on `_64`.

struct VSOutRate {
  float4 pos : SV_Position;
  uint rate : SV_ShadingRate;
};

struct VSOutPlain {
  float4 pos : SV_Position;
  float2 uv : TEXCOORD0;
};

struct PatchConst {
  float edges[3] : SV_TessFactor;
  float inside : SV_InsideTessFactor;
};

// --- self-test: SV_ShadingRate as a vertex shader output (VSOut = SV, and the
// --- VRS spec permits setting it from VS).
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

// --- HSCPIn: SV_ShadingRate on the hull shader's INPUT control point.
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

// --- HSCPOut: SV_ShadingRate on the hull shader's OUTPUT control point.
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

// --- DSCPIn: SV_ShadingRate on the domain shader's INPUT control point.
[domain("tri")]
VSOutPlain DSCPInMain(PatchConst pc, float3 bary : SV_DomainLocation,
                      const OutputPatch<VSOutRate, 3> patch) {
  VSOutPlain o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.uv = (float2)patch[0].rate;
  return o;
}

// --- DSOut: SV_ShadingRate on the domain shader's OUTPUT.
[domain("tri")]
VSOutRate DSOutMain(PatchConst pc, float3 bary : SV_DomainLocation,
                    const OutputPatch<VSOutPlain, 3> patch) {
  VSOutRate o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.rate = (uint)patch[0].uv.x;
  return o;
}
