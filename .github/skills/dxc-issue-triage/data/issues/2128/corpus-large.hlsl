// #2128 corpus -- the large end. Heavy straight-line math with an unrolled sample loop, so
// the ratio is measured where code, not container overhead, dominates the file.

cbuffer Params : register(b0) {
  float4   gOffsets[32];
  float4   gWeights[32];
  float4x4 gTransform;
  float4   gMisc;
};

Texture2D    gTex[4]   : register(t0);
SamplerState gSampler  : register(s0);

float3 Wave(float3 p, float k) {
  float3 s = sin(p * k);
  float3 c = cos(p * k * 1.37 + gMisc.x);
  return s * c + s.yzx * c.zxy;
}

float4 main(float4 pos : SV_Position, float2 uv : TEXCOORD0,
            float3 nrm : TEXCOORD1) : SV_Target {
  float3 acc = 0;
  float3 p = float3(uv, gMisc.y);

  [unroll]
  for (int i = 0; i < 32; ++i) {
    float2 offs = gOffsets[i].xy * gMisc.z;
    float4 s0 = gTex[0].Sample(gSampler, uv + offs);
    float4 s1 = gTex[1].Sample(gSampler, uv - offs);
    float4 s2 = gTex[2].Sample(gSampler, uv + offs.yx);
    float4 s3 = gTex[3].Sample(gSampler, uv - offs.yx);

    float3 mixed = s0.rgb * gWeights[i].x + s1.rgb * gWeights[i].y
                 + s2.rgb * gWeights[i].z + s3.rgb * gWeights[i].w;

    float3 w = Wave(p + gOffsets[i].zzw, gWeights[i].x + float(i));
    float3 tw = mul(float4(mixed + w, 1.0), gTransform).xyz;

    acc += tw * exp2(-abs(gOffsets[i].w)) + log2(abs(mixed) + 1.0);
    acc = normalize(acc + 1e-4) * length(acc);
    p += w * 0.031;
  }

  float3 n = normalize(nrm);
  acc *= saturate(dot(n, normalize(gMisc.xyz + 1e-3)));
  acc = pow(max(acc, 1e-5), 1.0 / 2.2);
  return float4(acc, 1.0);
}
