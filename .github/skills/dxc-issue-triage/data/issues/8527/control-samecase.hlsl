// NEGATIVE CONTROL for match.json. Identical to repro.hlsl except that the second
// chain spells the shared header in matching case. Must compile clean and must not
// match `redefinition of 'Foo'`; if it did, the predicate would be measuring double
// inclusion in general rather than the case bug.
#include "includeA.hlsli"          // -> cs_pragma.hlsli
#include "includeB-samecase.hlsli" // -> cs_pragma.hlsli   (same spelling)

RWStructuredBuffer<Foo> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x].m_scale = 1.0;
}
