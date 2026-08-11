// The reporter's second stated workaround: an explicit cast at the call site.
float4  main(uint texIdx: TIX, uint sampIdx : SIX, float2 coord: C) : SV_Target
{
    Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
    float4 result = myTexture.Sample(((SamplerState)SamplerDescriptorHeap[sampIdx]), coord);
    return result;
}
