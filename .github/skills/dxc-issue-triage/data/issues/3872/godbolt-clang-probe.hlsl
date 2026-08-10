// Issue 3872 -- narrow probe: what does Clang's HLSL front end currently know
// about SV_ShadingRate?  Published to Compiler Explorer as a separate, smaller
// source than godbolt-source.hlsl, for one reason: Clang parses the whole
// translation unit, so a file containing InputPatch/OutputPatch/[domain] would
// bury the answer under unrelated parse errors and the pane would be noise.
// Nothing here is stage-specific beyond a vertex entry point.
//
// The four panes differ in ONE thing at a time, so each reading is controlled:
//
//   hlsl_clang_trunk  -T cs_6_4 -E CSMain -DNO_RATE -fsyntax-only
//       CONTROL. Same file, same pane, same flags, with the declaration below
//       preprocessed out. If this is not clean, nothing else in the Clang
//       panes can be read -- silence and errors alike need a witness that the
//       pane works at all.
//   hlsl_clang_trunk  -T cs_6_4 -E CSMain -fsyntax-only
//       The same compile with the declaration put back. The ONLY difference
//       from the control is the semantic, so whatever changes is caused by it.
//   hlsl_clang_trunk  -T vs_6_4 -E VSRateMain -fsyntax-only
//       The same question asked at the entry point that uses it. -fsyntax-only
//       asks only what the front end can still answer, so an incomplete DXIL
//       backend cannot be mistaken for a diagnostic.
//   dxc_trunk         -T vs_6_4 -E VSRateMain
//       CONTROL. Proves this file is valid HLSL that DXC accepts, so a Clang
//       error here is about Clang, not about the file.
//
// VSOut is the position the D3D12 VRS spec permits, so no compiler should
// object to it on spec grounds. That is deliberate: this probe is about
// whether the semantic is modelled at all, not about who diagnoses what.

#ifndef NO_RATE
struct VSOutRate {
  float4 pos : SV_Position;
  uint rate : SV_ShadingRate;
};

VSOutRate VSRateMain(float4 pos : POSITION, uint rate : RATE) {
  VSOutRate o;
  o.pos = pos;
  o.rate = rate;
  return o;
}
#endif

RWBuffer<uint> Out : register(u0);

[numthreads(1, 1, 1)]
void CSMain(uint id : SV_DispatchThreadID) {
  Out[id] = id;
}
