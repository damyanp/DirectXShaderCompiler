int2x2 m;
RWStructuredBuffer<int2> output;

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
	int2 b;
	b.x = tid.x;
	output[0] = mul(b, m);
}
