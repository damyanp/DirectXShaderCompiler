// Negative control: same shape (two static globals, one initialising the
// other) but the entry point only reaches POINT_SIZE directly -- there is no
// transitive chain, so a correct rewriter keeps POINT_SIZE and removes
// nothing that is still referenced. Must recompile clean (no-match).
static const float POINT_SIZE = 3.0f;

struct PSInput
{
    float4 position : POSITION;
};

PSInput VSMain(float3 position : POSITION)
{
    PSInput psInput;
    psInput.position = float4(position, 1.0f);
    psInput.position.xyz *= POINT_SIZE;
    return psInput;
}
