// Is the cbuffer array load-bearing? Same self-initialised index, but used to index a
// Buffer<float4> instead of a constant-buffer array, so the legacy cbuffer GEP translation
// in HLOperationLower.cpp is never reached.
Buffer<float4> colors : register(t0);

float4 PSMain() : SV_TARGET
{
    uint index = index; // Initializing a variable to itself is bad!
    return colors[index];
}
