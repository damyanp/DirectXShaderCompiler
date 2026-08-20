static const float POINT_SIZE = 3.0f;
static const float3 POINT_SIZE_3 = float3(1.0f, 1.0f, 1.0f) * POINT_SIZE;

struct PSInput
{
    float4 position : POSITION;
};

PSInput VSMain(float3 position : POSITION)
{
    PSInput psInput;
    psInput.position = float4(position, 1.0f);
    psInput.position.xyz *= POINT_SIZE_3;
    return psInput;
}
