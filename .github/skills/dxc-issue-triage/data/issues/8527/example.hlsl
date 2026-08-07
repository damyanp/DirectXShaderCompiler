// REJECTED DEMONSTRATION -- retained as evidence of why #8527 has no Compiler Explorer
// link. Do not cite this file as showing the bug.
//
// The idea was to squeeze the multi-file repro into CE's single file by having the file
// include ITSELF under a different spelling of its own path ("./example.hlsl" vs the
// "example.hlsl" the driver was given). It does produce `error: redefinition of 'Foo'`,
// locally and on CE's Linux builds.
//
// But selfsame.hlsl is the same construction with a MATCHING spelling, and it produces
// the same error. So this device measures clang's documented rule that `#pragma once` is
// ignored in the main file (hence the -Wpragma-once-outside-header warning it emits), not
// #8527's path-spelling defect. See variant-selfinclude-samespelling-main-debug.txt.
#pragma once

struct Foo { float4 m_scale; };

#ifndef SECOND_PASS
#define SECOND_PASS
#include "./example.hlsl"

RWStructuredBuffer<Foo> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x].m_scale = 1.0;
}
#endif
