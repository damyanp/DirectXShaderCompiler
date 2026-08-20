// Negative control: same two static globals and the same initializer chain
// as repro.hlsl, but the entry point never references POINT_SIZE_3 (or
// POINT_SIZE) at all. A correct rewriter removes both -- there is nothing
// left in the rewritten source that could reference a missing identifier, so
// this must recompile clean (no-match). This proves the predicate is not
// simply satisfied by "the rewriter removed a static const global".
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
    return psInput;
}
