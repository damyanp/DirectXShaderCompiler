// #2128 -- medium, realistic forward-lit pixel shader.
//
// The issue supplied no code at all, so this corpus is agent-constructed. It is written to
// the intersection of what fxc (ps_5_1) and dxc (ps_6_0) both accept, because the whole
// claim is a comparison between the two compilers' output for "same shaders".
//
// Nothing here is SM6-only, and nothing is chosen to make either compiler look bad: it is
// ordinary shader work -- cbuffer reads, texture fetches, a light loop, some transcendentals.

cbuffer PerFrame : register(b0) {
  float4x4 gViewProj;
  float4   gEyePos;
  float4   gLightPos[8];
  float4   gLightColor[8];
  float4   gFogParams;
  int      gLightCount;
};

Texture2D    gAlbedo   : register(t0);
Texture2D    gNormal   : register(t1);
Texture2D    gRoughness : register(t2);
SamplerState gSampler  : register(s0);

struct VSOut {
  float4 pos    : SV_Position;
  float3 world  : TEXCOORD0;
  float3 normal : TEXCOORD1;
  float3 tangent : TEXCOORD2;
  float2 uv     : TEXCOORD3;
};

float3 FresnelSchlick(float3 f0, float cosTheta) {
  float m = saturate(1.0 - cosTheta);
  float m2 = m * m;
  return f0 + (1.0 - f0) * (m2 * m2 * m);
}

float DistributionGGX(float ndoth, float roughness) {
  float a = roughness * roughness;
  float a2 = a * a;
  float d = ndoth * ndoth * (a2 - 1.0) + 1.0;
  return a2 / max(3.14159265 * d * d, 1e-6);
}

float GeometrySmith(float ndotv, float ndotl, float roughness) {
  float k = (roughness + 1.0) * (roughness + 1.0) * 0.125;
  float gv = ndotv / (ndotv * (1.0 - k) + k);
  float gl = ndotl / (ndotl * (1.0 - k) + k);
  return gv * gl;
}

float4 main(VSOut input) : SV_Target {
  float4 albedo = gAlbedo.Sample(gSampler, input.uv);
  float3 nmap = gNormal.Sample(gSampler, input.uv).xyz * 2.0 - 1.0;
  float roughness = gRoughness.Sample(gSampler, input.uv).r;

  float3 n = normalize(input.normal);
  float3 t = normalize(input.tangent - n * dot(n, input.tangent));
  float3 b = cross(n, t);
  float3 normal = normalize(nmap.x * t + nmap.y * b + nmap.z * n);

  float3 v = normalize(gEyePos.xyz - input.world);
  float ndotv = saturate(dot(normal, v));
  float3 f0 = lerp(0.04, albedo.rgb, albedo.a);

  float3 acc = 0;
  for (int i = 0; i < gLightCount; ++i) {
    float3 toLight = gLightPos[i].xyz - input.world;
    float dist2 = dot(toLight, toLight);
    float3 l = toLight * rsqrt(max(dist2, 1e-6));
    float3 h = normalize(l + v);

    float ndotl = saturate(dot(normal, l));
    float ndoth = saturate(dot(normal, h));
    float vdoth = saturate(dot(v, h));

    float atten = 1.0 / (1.0 + dist2 * gLightPos[i].w);
    float3 fres = FresnelSchlick(f0, vdoth);
    float dist = DistributionGGX(ndoth, roughness);
    float geo = GeometrySmith(ndotv, ndotl, roughness);

    float3 spec = fres * dist * geo / max(4.0 * ndotv * ndotl, 1e-4);
    float3 diff = (1.0 - fres) * albedo.rgb * (1.0 / 3.14159265);
    acc += (diff + spec) * gLightColor[i].rgb * ndotl * atten;
  }

  float depth = distance(gEyePos.xyz, input.world);
  float fog = saturate((depth - gFogParams.x) / max(gFogParams.y - gFogParams.x, 1e-3));
  acc = lerp(acc, gFogParams.zzz, fog);

  acc = acc / (acc + 1.0);
  acc = pow(max(acc, 1e-5), 1.0 / 2.2);
  return float4(acc, albedo.a);
}
