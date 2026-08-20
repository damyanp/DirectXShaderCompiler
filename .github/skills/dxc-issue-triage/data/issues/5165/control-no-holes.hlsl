RWStructuredBuffer<uint> buf : register(u0);

[numthreads(1,1,1)]
void ShaderDomain_Cs(uint3 id : SV_DispatchThreadID)
{
    uint x = buf[0];
    bool result;
    switch (x)
    {
    case 0: result = true; break;
    case 1: result = true; break;
    case 2: result = true; break;
    case 3: result = true; break;
    case 4: result = true; break;
    case 5: result = true; break;
    case 6: result = true; break;
    default: result = (buf[1] != 0);
    }
    buf[0] = result ? 1 : 0;
}
