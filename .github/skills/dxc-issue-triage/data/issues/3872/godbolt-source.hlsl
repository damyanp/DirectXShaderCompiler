// Issue 3872 -- the source published to Compiler Explorer.
//
// It is repro.hlsl plus three CONTROL entry points, in one file, so that the
// link carries its own control: the same compiler, the same stage and the same
// semantic, once in a cell the interpretation table marks SV and once in a cell
// it marks NA. A link that only showed acceptance would be unreadable, because
// silence has an innocent explanation (nothing was checked) that a reader
// cannot rule out from the outside.
//
// What each pane compiles, and what to look at:
//
//   -T ds_6_4 -E DSOutMain    ACCEPTED. The D3D12 Variable Rate Shading spec
//                             says the rate may be set from VS, GS or MS and
//                             "It is not permitted from other stages, for
//                             example DS". Look at the Output signature table:
//                             the row's SysValue column says SHDINGRATE, so
//                             this was lowered as a system value, not treated
//                             as an arbitrary semantic.
//   -T ds_6_4 -E DSInBad      CONTROL, same compiler and stage: DXC does have
//                             this diagnostic and does reach it here.
//   -T hs_6_4 -E HSCPInMain   ACCEPTED, hull shader input control point.
//   -T hs_6_4 -E HSPCOutBad   CONTROL, same compiler and stage.
//   dxc_1_6_2112 ds_6_4       The release closest to the report date, same
//                             result: this is not a recent regression.
//
// Locally this file is compiled by `triage.py run --shader godbolt-source.hlsl
// --label ce`, so the published source is not an untested variant of the repro.

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

// The same struct with the rate moved into the patch-constant signature, which
// the table marks NA for both PCOut and DSIn.
struct PatchConstSR {
  float edges[3] : SV_TessFactor;
  float inside : SV_InsideTessFactor;
  uint rate : SV_ShadingRate;
};

// ---------------------------------------------------------------- accepted --
// SV_ShadingRate as a vertex shader output: permitted by the VRS spec, and the
// reason a reader can tell this build knows the semantic at all.
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

// HSCPIn: the hull shader's INPUT control point carries SV_ShadingRate.
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

// HSCPOut: the hull shader's OUTPUT control point carries SV_ShadingRate.
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

// DSCPIn: the domain shader's INPUT control point carries SV_ShadingRate.
[domain("tri")]
VSOutPlain DSCPInMain(PatchConst pc, float3 bary : SV_DomainLocation,
                      const OutputPatch<VSOutRate, 3> patch) {
  VSOutPlain o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.uv = (float2)patch[0].rate;
  return o;
}

// DSOut: the domain shader WRITES SV_ShadingRate. This is the position the VRS
// spec rules out by name.
[domain("tri")]
VSOutRate DSOutMain(PatchConst pc, float3 bary : SV_DomainLocation,
                    const OutputPatch<VSOutPlain, 3> patch) {
  VSOutRate o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.rate = (uint)patch[0].uv.x;
  return o;
}

// ----------------------------------------------------------------- controls --
// The same semantic in three cells the same table already marks NA, so a reader
// can see the diagnostic exists and fires in these very stages.

// VSIn is NA: expect "invalid semantic 'SV_ShadingRate' for vs 6.4".
VSOutPlain VSInBad(float4 pos : POSITION, uint rate : SV_ShadingRate) {
  VSOutPlain o;
  o.pos = pos;
  o.uv = (float2)rate;
  return o;
}

PatchConstSR PCMainBad(InputPatch<VSOutPlain, 3> ip) {
  PatchConstSR c;
  c.edges[0] = 1;
  c.edges[1] = 1;
  c.edges[2] = 1;
  c.inside = 1;
  c.rate = 1;
  return c;
}

// PCOut is NA: expect "Semantic SV_ShadingRate is invalid for shader model: hs".
[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("PCMainBad")]
VSOutPlain HSPCOutBad(InputPatch<VSOutPlain, 3> ip, uint i : SV_OutputControlPointID) {
  VSOutPlain o;
  o.pos = ip[i].pos;
  o.uv = ip[i].uv;
  return o;
}

// DSIn is NA: expect "Semantic SV_ShadingRate is invalid for shader model: ds".
[domain("tri")]
VSOutPlain DSInBad(PatchConstSR pc, float3 bary : SV_DomainLocation,
                   const OutputPatch<VSOutPlain, 3> patch) {
  VSOutPlain o;
  o.pos = patch[0].pos * bary.x + patch[1].pos * bary.y + patch[2].pos * bary.z;
  o.uv = (float2)pc.rate;
  return o;
}
