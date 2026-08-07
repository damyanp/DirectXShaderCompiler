// Is the include-once state keyed on the *spelled path* rather than on file identity?
// Same case throughout; the second chain spells the shared header "./cs_pragma.hlsli".
// If this reproduces too, the defect is broader than letter case.
#include "includeA.hlsli"          // -> cs_pragma.hlsli
#include "includeB-dotslash.hlsli" // -> ./cs_pragma.hlsli  (same file, same case)

RWStructuredBuffer<Foo> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x].m_scale = 1.0;
}
