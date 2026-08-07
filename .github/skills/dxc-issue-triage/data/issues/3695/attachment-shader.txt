#define MY_RS    "RootFlags(0),"  \
    "CBV(b0), " \
    "DescriptorTable(UAV(u0, numDescriptors = 3)) " 




// Each #kernel tells which function to compile; you can have many kernels
//#pragma kernel BlurShader
RWTexture2D<float4> _blurResult;

RWTexture2D<float4> _previousResult;

RWTexture2D<float4> _previousTarget;

float _blendFactor,_blurSize, _blurDirections, _blurQuality;

RWTexture2D<float4> blur(RWTexture2D<float4> tex, float2 uv, float2 stride)
{
	float Pi = 6.28318530718; // Pi*2

	float2 Radius = _blurSize / stride;

	float4 Color = tex[uv];

	// Blur calculations
	for (float d = 0.0; d < Pi; d += Pi / _blurDirections)
	{
		float2 angles = float2(cos(d), sin(d));

		for (float i = 1.0 / _blurQuality; i <= 1.0; i += 1.0 / _blurQuality)
		{
			Color.r += tex[uv + angles * Radius * i].r;
		}
	}

	float divisor = _blurQuality * _blurDirections - 15.0;
	if (divisor == 0)
	{
		divisor = 0.0001;
	}
	Color.r /= divisor;

	tex[uv] = Color;
    
    //return Color;
	return tex;
}

[RootSignature(MY_RS)]
[numthreads(8,8,1)]
void main(uint3 id : SV_DispatchThreadID)
{
	float x, y;
	_blurResult.GetDimensions(x, y);
	RWTexture2D<float4> filterFog = blur(_blurResult, id.xy, float2(x, y));

	_previousResult[id.xy] = lerp(_previousResult[id.xy], _previousTarget[id.xy], _blendFactor);
	_blurResult = filterFog;
}