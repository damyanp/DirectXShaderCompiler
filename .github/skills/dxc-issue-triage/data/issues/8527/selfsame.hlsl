// CONTROL for the single-file device in example.hlsl.
//
// Identical construction, except this file includes itself under the SAME spelling the
// driver was given ("selfsame.hlsl"). If it still redefines 'Foo', the self-include
// device is measuring clang's documented rule that `#pragma once` is ignored in the
// main file (-Wpragma-once-outside-header) rather than #8527's path-spelling defect,
// and is therefore useless as a demonstration.
#pragma once

struct Foo { float4 m_scale; };

#ifndef SECOND_PASS
#define SECOND_PASS
#include "selfsame.hlsl"

RWStructuredBuffer<Foo> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x].m_scale = 1.0;
}
#endif
