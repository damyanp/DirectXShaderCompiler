#define MAX_CLIPPINGPLANES_CASCADE_ 8

struct VSOUT
{
	float4 vPos:SV_Position;
	float4 afClipD[MAX_CLIPPINGPLANES_CASCADE_>>2]:SV_ClipDistance;
};

void castFunc(out float4 afClipD[MAX_CLIPPINGPLANES_CASCADE_>>2])
{
	[unroll]
	for (int n=0;n<MAX_CLIPPINGPLANES_CASCADE_;++n)
		((float[MAX_CLIPPINGPLANES_CASCADE_])afClipD)[n]=float(n*n);
}

VSOUT main(float4 pos:POSITION0)
{
	VSOUT ret;
	ret.vPos=1;
	castFunc(ret.afClipD);	
	return ret;
} 
