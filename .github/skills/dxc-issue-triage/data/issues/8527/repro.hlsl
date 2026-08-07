// #8527 minimised repro. Structure is the reporter's; the entry point is trimmed to
// the smallest thing that still compiles, and the profile lowered to cs_6_0 so that
// every release back to the v1.4.1907 floor is a valid probe. The reporter's verbatim
// main + -T cs_6_6 is kept in as-filed.hlsl / cmd-as-filed.txt.
#include "includeA.hlsli"          // -> cs_pragma.hlsli
#include "includeB.hlsli"          // -> cs_Pragma.hlsli   (same file, capital 'P')

RWStructuredBuffer<Foo> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x].m_scale = 1.0;
}
