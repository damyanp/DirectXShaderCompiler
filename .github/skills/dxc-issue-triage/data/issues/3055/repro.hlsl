Texture2D<float4> tex;
SamplerComparisonState samp;

float4 main(float2 coord : C) : SV_Target {
  return tex.Sample(samp, coord);
}
