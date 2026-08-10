cbuffer cb0 : register(b0)
{
    float4 colors[4];
}

float4 PSMain() : SV_TARGET
{
    uint index = index; // Initializing a variable to itself is bad!
    return colors[index];
}
