// #3259 variant: a different HLSL object type in the payload, to show the trigger is
// dxilutil::IsHLSLObjectType (lib/HLSL/HLLowerUDT.cpp:65) and not Texture2D specifically.
SamplerState g_sampler;

struct smallPayload
{
	SamplerState samp;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.samp = g_sampler;
    DispatchMesh(1, 1, 1, p);
}
