// #2128 corpus -- the small end. A near-trivial pixel shader, included so the measurement
// shows how much of the answer is fixed container overhead rather than code size.

cbuffer Tint : register(b0) { float4 gTint; };

Texture2D    gTex     : register(t0);
SamplerState gSampler : register(s0);

float4 main(float4 pos : SV_Position, float2 uv : TEXCOORD0) : SV_Target {
  return gTex.Sample(gSampler, uv) * gTint;
}
