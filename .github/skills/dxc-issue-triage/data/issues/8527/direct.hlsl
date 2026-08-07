// Minimised form: no intermediate headers. Two include directives in one file,
// differing only in the case of the file name. Two files total.
#include "cs_pragma.hlsli"
#include "cs_Pragma.hlsli"

RWStructuredBuffer<Foo> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x].m_scale = 1.0;
}
