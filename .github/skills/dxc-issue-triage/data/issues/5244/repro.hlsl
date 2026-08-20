RWTexture2DMS<uint4, 2>    gUav : register(u1);

struct VSINPUT
{
    float3 Pos : POSITION;

};

struct VSOUTPUT
{
    float4 Pos : SV_POSITION;

};

VSOUTPUT VS(VSINPUT vin)
{
    VSOUTPUT vout = (VSOUTPUT) 0.0f;

    return vout;
}

float4 PS(VSOUTPUT pin) : SV_Target
{

    uint4 col = gUav[(uint2) pin.Pos.xy]; 

    gUav.sample[1][uint2(pin.Pos.xy)] = col;
	uint4 outColor = gUav.sample[1][uint2(pin.Pos.xy)];
    return outColor;

}

