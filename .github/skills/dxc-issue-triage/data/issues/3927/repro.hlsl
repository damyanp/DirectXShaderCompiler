struct PixelInput
{
	float4 pos : SV_Position0;
	float2 texCoord : TEXCOORD0;
};

Texture2D Tex0;
SamplerState SS0;
Texture2D Tex1;
SamplerState SS1;

float4 main(in PixelInput In) : SV_Target0
{
	const float2 val = Tex0.Sample(SS0, In.texCoord).xy;
	if (((val.x == 0.0f) && (val.y == 0.0f)))
	{
		clip(-1.0f);
	}
	clip(-0.5f);
	return Tex1.Sample(SS1, In.texCoord);
}
