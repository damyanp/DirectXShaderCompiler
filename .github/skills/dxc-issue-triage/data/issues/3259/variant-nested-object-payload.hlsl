// #3259 variant: the object is one level deeper, inside a nested struct.
// Exercises GetLoweredUDT's recursive failure propagation
// (lib/HLSL/HLLowerUDT.cpp:70 "NewTy = GetLoweredUDT(ST); if (nullptr == NewTy) return nullptr;")
// rather than the direct IsHLSLObjectType check.
Texture2D<float4> g_texture;

struct inner
{
	Texture2D<float4> texture;
};

struct smallPayload
{
	inner i;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.i.texture = g_texture;
    DispatchMesh(1, 1, 1, p);
}
