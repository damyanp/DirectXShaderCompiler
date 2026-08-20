#define MAX_CLIPPINGPLANES_CASCADE_ 8

struct VSOUT
{
	float4 vPos:SV_Position;
	float4 afClipD[MAX_CLIPPINGPLANES_CASCADE_>>2]:SV_ClipDistance;
};

// Same subject as repro.hlsl (an out float4[] array parameter, assigned
// element-by-element inside an [unroll] loop) but without the reinterpret
// cast to a differently-sized float[] array. This is ordinary, well-formed
// HLSL and must compile cleanly -- it proves the predicate does not fire on
// unrelated array/SROA code, only on the specific cast construct.
void castFunc(out float4 afClipD[MAX_CLIPPINGPLANES_CASCADE_>>2])
{
	[unroll]
	for (int n=0;n<MAX_CLIPPINGPLANES_CASCADE_>>2;++n)
		afClipD[n]=float4(n*n,n*n,n*n,n*n);
}

VSOUT main(float4 pos:POSITION0)
{
	VSOUT ret;
	ret.vPos=1;
	castFunc(ret.afClipD);	
	return ret;
} 
