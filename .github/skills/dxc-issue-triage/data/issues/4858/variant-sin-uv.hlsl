Texture2D<float> T;
RWTexture2D<uint> A;
SamplerState S;

float4 main(float2 uv : UV) : SV_Target
{
	float l = T.CalculateLevelOfDetailUnclamped(S, sin(uv));
	if (all(uv < 0.5))
	{
		uint il = uint(max(l, 0.0) * 32);
		uint o;
		InterlockedMin(A[int2(uv)], il, o);
	}

	return T.Sample(S, uv);
}
