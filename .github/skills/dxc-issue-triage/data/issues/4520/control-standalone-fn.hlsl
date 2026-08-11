// Source of https://godbolt.org/z/bPxKTo4q4, posted by damyanp on 2024-07-31, read back
// verbatim from GET https://godbolt.org/api/shortlinkinfo/bPxKTo4q4. The same subscript
// expression is passed to a user-defined function whose parameter is a SamplerState.
float4 Standalone(Texture2D<float4> texture, SamplerState state, float2 coord) {
    return texture.Sample(state, coord);
}


float4  main(uint texIdx: TIX, uint sampIdx : SIX, float2 coord: C) : SV_Target
{
    Texture2D<float4> myTexture = ResourceDescriptorHeap[texIdx];
    float4 result = Standalone(myTexture, SamplerDescriptorHeap[sampIdx], coord);
    //myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
    return result;
}
