float4 main(float2 uv : UV) : SV_Target
{
	if (all(uv < 0.5))
	{
		return float4(1, 0, 0, 1);
	}
	return float4(0, 1, 0, 1);
}
