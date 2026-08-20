// Repro for https://github.com/microsoft/DirectXShaderCompiler/issues/5801
// "Sample immediate offset range is not diagnosed or validated in SM 6.7"
//
// Reporter's exact shader from the issue body. In SM 6.6 and earlier this is
// diagnosed with:
//   error: Offsets to texture access operations must be between -8 and 7.
// In SM 6.7+ the issue claims no diagnostic and no DXIL validation error is
// produced, even though the immediate offset (12, -14) is outside the
// DXIL-legal [-8, 7] range.

Texture2D T2D;
SamplerState S;

float4 main(float2 coord : TEXCOORD) : SV_Target {
  return T2D.Sample(S, coord, int2(12, -14));
}
