// #3726 VARIANT -- the shape PR #3721 was actually about, which this issue was filed
// out of (jaebaek: "This is the first issue mentioned by ...pull/3721#issuecomment-
// 829537469"). There x0/x1/x2 are FUNCTION-LOCAL variables, not globals and not
// statics:
//
//     void main() { Texture2D<float4> x; getResource(x); ... }
//
// Committed as the third point of the comparison: local, static, global. Only one of
// the three is rejected by anything.
Texture2D<float4>               r0;
SamplerState                    r1;
RWByteAddressBuffer             r2;

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
    Texture2D<float4>   x0;
    SamplerState        x1;
    RWByteAddressBuffer x2;
    getResource(x0, x1, x2);
    return x0.Sample(x1, float2(x2.Load(0), x2.Load(1)));
}
