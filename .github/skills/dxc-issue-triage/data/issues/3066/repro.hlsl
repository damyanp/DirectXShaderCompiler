// Repro for issue #3066 -- "Improved human-readable values in disassembly".
// Agent-constructed: the issue quotes one disassembly line and ships no shader.
//
// Built so that a single disassembly listing contains one instance of each of
// the five things the reporter asked to be made readable:
//   B  a float constant feeding a binary dx.op  -> max(..., 0.0001)
//   C  non-unary/binary dx.op classes           -> loadInput / storeOutput
//   D  loads and stores through a named resource
//   E  the Resource Bindings table, and the ViewID output-dependency table
//   A  per-instruction source location          -> needs -Zi -Qembed_debug

Texture2D<float4> g_diffuseTexture : register(t0);
SamplerState g_linearSampler : register(s0);
RWStructuredBuffer<float> g_luminanceOut : register(u0);

cbuffer PerFrame : register(b0) {
  float g_exposure;
}

struct PSInput {
  float4 pos : SV_Position;
  float2 uv : TEXCOORD0;
};

float4 main(PSInput input) : SV_Target {
  float4 texel = g_diffuseTexture.Sample(g_linearSampler, input.uv);
  float lum = dot(texel.rgb, float3(0.299, 0.587, 0.114));
  float safe = max(lum * g_exposure, 0.0001);
  g_luminanceOut[0] = safe;
  return float4(texel.rgb / safe, texel.a);
}
