// #4256 repro (agent-constructed).
//
// A vertex shader that (a) reads SV_ViewID and lets an output depend on it,
// and (b) copies a signature input into a signature output. Both facts are
// recorded in the DXIL module's serialized ViewID state:
//   - OutputsDependentOnViewId  (from `pos`, which adds `vid`)
//   - InputsContributingToOutputs (from `col`, which is copied through)
// SV_ViewID requires shader model 6.1.

struct VSOut {
  float4 pos : SV_Position;
  float4 col : COLOR;
};

VSOut main(float4 pos : POSITION, float4 col : COLOR, uint vid : SV_ViewID) {
  VSOut o;
  o.pos = pos + (float)vid;
  o.col = col;
  return o;
}
