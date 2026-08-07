// Does a classic #ifndef/#define include guard survive the case mismatch that
// #pragma once does not? The guard macro is global to the translation unit, so the
// second inclusion should be an empty no-op even if the file is entered twice.
// This is the workaround to recommend, so it has to be measured, not assumed.
#include "guardedA.hlsli"   // -> guarded-common.hlsli
#include "guardedB.hlsli"   // -> Guarded-Common.hlsli  (same file, different case)

RWStructuredBuffer<Foo> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x].m_scale = 1.0;
}
