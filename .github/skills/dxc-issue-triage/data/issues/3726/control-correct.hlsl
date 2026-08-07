// #3726 NEGATIVE CONTROL -- correct code, must not match either predicate.
//
// repro.hlsl with the assignment-to-resource removed: main uses the globals
// directly instead of laundering them through `out` resource parameters.
// Everything else is the same, so the two inputs differ in exactly one way.
//
// match.json      must NOT match: no DXIL back-end resource error.
// match-sema.json must NOT match: no front-end diagnostic either.
Texture2D<float4>               r0;
SamplerState                    r1;
RWByteAddressBuffer             r2;

float4 main(): SV_Target
{
    return r0.Sample(r1, float2(r2.Load(0), r2.Load(1)));
}
