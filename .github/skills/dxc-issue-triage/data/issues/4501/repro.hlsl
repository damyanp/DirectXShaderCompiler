// Minimal pixel shader used to ask whether DXC's SPIR-V backend ever emits the
// split-debug-info instructions requested in issue 4501.
//
// Deliberately does NOT spell either requested instruction name anywhere: with
// -fspv-debug=vulkan-with-source the shader text is embedded in the module, so a
// mention here would manufacture a hit and make the absence clauses unfalsifiable.
// The mirror case is control-tokens-in-source.hlsl.

float4 g_color;

float4 main(float4 pos : SV_Position) : SV_Target {
  float4 acc = g_color;
  for (int i = 0; i < 2; ++i) {
    acc = acc * 0.5f + pos;
  }
  return acc;
}
