// #3726 VARIANT -- the repro as damyanp's 2024-07-16 comment says it was meant to be:
// "(For reference, x0, x1 and x2 in the repro should be static)".
//
// Identical to repro.hlsl except that x0/x1/x2 are `static` rather than bound
// resource declarations. Run it before deciding what the issue is about: the DXIL
// result is the OPPOSITE of the as-filed repro's.
Texture2D<float4>               r0;
SamplerState                    r1;
RWByteAddressBuffer             r2;

static Texture2D<float4>        x0;
static SamplerState             x1;
static RWByteAddressBuffer      x2;

void getResource(out    Texture2D<float4>               a0,
                 out    SamplerState                    a1,
                 out    RWByteAddressBuffer             a2)
{
    a0 = r0;
    a1 = r1;
    a2 = r2;
}

float4 main(): SV_Target
{
    getResource(x0, x1, x2);
    return x0.Sample(x1, float2(x2.Load(0), x2.Load(1)));
}
