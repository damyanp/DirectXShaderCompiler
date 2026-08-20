// Control for the primary (ps_6_6 / PSMain) predicate. Same stage/profile as repro.hlsl so it
// can run through `run --shader ... --label control`. Uses the pattern tex3d's comment
// identifies as supported today: NonUniformResourceIndex wraps the *immediate* index of the
// ResourceDescriptorHeap built-in array directly, with no intermediate array-of-resource-objects.
// Must compile cleanly and must NOT print "All metadata must be used by dxil".
struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

cbuffer Ids {
    int id1;
};

SamplerState ss: register(s0);

float4 PSMain(PSInput input) : SV_Target0
{
    Texture2D<float4> tex = ResourceDescriptorHeap[NonUniformResourceIndex(id1)];
    float4 sample = tex.Sample(ss, float2(0, 1));
    return sample;
}
