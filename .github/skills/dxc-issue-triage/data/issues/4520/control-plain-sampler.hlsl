// No descriptor heaps at all: an ordinary declared SamplerState passed to Sample. Proves the
// predicate does not fire on an unremarkable, correct Sample call under the same command.
Texture2D<float4> myTexture;
SamplerState mySampler;

float4  main(float2 coord: C) : SV_Target
{
    return myTexture.Sample(mySampler, coord);
}
