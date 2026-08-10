cbuffer cb0 : register(b0)
{
    float4 colors[4];
}

float4 PSMain() : SV_TARGET
{
    uint index = 0; // The same shader, with the self-initialisation removed.
    return colors[index];
}
