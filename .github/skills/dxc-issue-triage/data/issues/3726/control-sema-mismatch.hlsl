// #3726 POSITIVE CONTROL for match-sema.json -- the front end DOES diagnose this.
//
// The same `a0 = r0;` assignment as repro.hlsl, at the same place, with only the
// resource TYPES swapped so the assignment is ill-typed. Sema rejects it:
//
//   error: cannot convert from 'Texture2D<float4>' to '__restrict SamplerState'
//
// Two things this proves, and they are the reason it is committed:
//  1. match-sema.json can fire at all -- a predicate that can never match is
//     indistinguishable from a compiler that never diagnoses;
//  2. the front end is not merely absent from this code path. It type-checks the
//     very expression #3726 is about; it simply has no rule that says assigning a
//     resource is itself illegal.
//
// match.json      must NOT match: Sema stops the compile, so the DXIL lowering
//                 passes never run and cannot emit their resource error.
// match-sema.json MUST match.
Texture2D<float4>               r0;
SamplerState                    r1;

Texture2D<float4>               x0;
SamplerState                    x1;

void getResource(out SamplerState a0, out Texture2D<float4> a1)
{
    a0 = r0;
    a1 = r1;
}

float4 main(): SV_Target
{
    getResource(x1, x0);
    return x0.Sample(x1, float2(0, 0));
}
