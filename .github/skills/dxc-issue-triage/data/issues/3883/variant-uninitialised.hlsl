// Is the self-initialisation load-bearing, or does any uninitialised index do it?
// Same shader as repro.hlsl with `uint index = index;` replaced by a plain uninitialised
// declaration, which is the far more common real-world spelling.
cbuffer cb0 : register(b0)
{
    float4 colors[4];
}

float4 PSMain() : SV_TARGET
{
    uint index;
    return colors[index];
}
