// The reporter's first stated workaround, and the feature-presence control for this issue:
// the smallest shader that uses BOTH ResourceDescriptorHeap and SamplerDescriptorHeap and is
// expected to compile. A release on which this fails cannot answer anything about #4520.
float4  main(uint texIdx: TIX, uint sampIdx : SIX, float2 coord: C) : SV_Target
{
    Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
    SamplerState mySampler = SamplerDescriptorHeap[sampIdx];
    float4 result = myTexture.Sample(mySampler, coord);
    return result;
}
