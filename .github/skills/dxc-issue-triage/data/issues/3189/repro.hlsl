Texture2D g_texture2D;
sampler g_sampler;

cbuffer a //unused
{
	float4x4 g_a;
};
cbuffer b //unused
{
	float4x4 g_b;
};
cbuffer c //used
{
	float4x4 g_localToClip;
	float4 g_randomOffset;
	float4  g_colorAdd;
};

float4 mainPS( float3 vTexCoord : TEXCOORD, float4 vColor : COLOR ) : SV_Target
{
	return (g_texture2D.Sample( g_sampler, vTexCoord.xy ) * vColor) + g_colorAdd;
}
