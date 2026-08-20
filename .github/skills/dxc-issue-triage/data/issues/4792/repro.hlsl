RWBuffer<float> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 id : SV_DispatchThreadID)
{
    Out[id.x] = 1.0;
}
