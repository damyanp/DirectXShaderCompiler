RWStructuredBuffer<uint> buf : register(u0);

float4 main(float4 pos : SV_Position) : SV_Target
{
    if (pos.x < 0)
    {
        discard;
    }
    buf[0] = 42;
    return float4(1,1,1,1);
}