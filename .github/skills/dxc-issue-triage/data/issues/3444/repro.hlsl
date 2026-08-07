RWStructuredBuffer<float4> rwTexture;

[numthreads(1, 1, 1)]
void CSMain(float id : SV_DispatchThreadID)
{
	rwTexture[3] = id.xxxx;
}
