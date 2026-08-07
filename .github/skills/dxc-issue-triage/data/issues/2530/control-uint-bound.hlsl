// Negative control for #2530's predicate.
// Identical to repro.hlsl except that the array bound is a `static const uint`
// initialised from an integer literal -- no type conversion anywhere. This is
// the supported spelling, so a predicate that fires here does not discriminate
// between "DXC rejects a converted constant" and "DXC rejects constant array
// bounds at all".
static const uint ARRAY_SIZE = 1;

float4 main() : SV_Target
{
    float array[ARRAY_SIZE] = { 1.0f };
    return (float4)0;
}
