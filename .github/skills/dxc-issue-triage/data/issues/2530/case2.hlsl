// microsoft/DirectXShaderCompiler#2530 -- case 2, verbatim from the issue body.
// The conversion happens one step earlier, into a `static const uint`, which is
// then used as the array bound.
static const float ARRAY_SIZE = 1;
static const uint ARRAY_SIZE_UINT = (uint)ARRAY_SIZE;

float4 main() : SV_Target
{
    float array[ARRAY_SIZE_UINT] = { 1.0f };
    return (float4)0;
}
