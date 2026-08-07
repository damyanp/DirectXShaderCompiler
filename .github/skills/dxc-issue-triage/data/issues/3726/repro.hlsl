// #3726 -- verbatim from the issue body (2021-04-29). Not reformatted: the
// diagnostics quote line and column numbers, so the layout is evidence.
Texture2D<float4>               r0;
SamplerState                    r1;
RWByteAddressBuffer             r2;

Texture2D<float4>               x0;
SamplerState                    x1;
RWByteAddressBuffer             x2;

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
