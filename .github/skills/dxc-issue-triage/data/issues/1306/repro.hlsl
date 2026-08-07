RWBuffer<uint> g_buf0;
RWBuffer<uint> g_buf1;
groupshared uint g_scratch[64];
[numthreads(64, 1, 1)]
void main(uint3 dtid : SV_DispatchThreadID)
{
    g_scratch[dtid.x] = g_buf0[dtid.x];
    if((dtid.x & 1) == 0)
    {
        GroupMemoryBarrierWithGroupSync();
        g_buf1[dtid.x/2] = g_scratch[dtid.x] + g_scratch[dtid.x + 1];
    }
}
