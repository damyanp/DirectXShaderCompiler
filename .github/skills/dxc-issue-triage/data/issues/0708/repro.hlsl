Texture2D tex : register(t1[27]);
float4 main() : SV_Target { return tex.Load(int3(0, 0, 0)); }
