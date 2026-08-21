// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-non-uniform-resource-index-instrumentation | %FileCheck %s

// The annotation prepass inlines away every non-entry function of a non-library
// module, because PIX's debugger cannot attribute a separately instrumented
// function to an invocation - see PIXPassHelpers::InlineNonEntryFunctions. That
// prepass is shared with the non-uniform-resource-index pipeline, which runs it
// for the instruction ordinals its diagnostics are addressed to, so this checks
// that an unqualified dynamic index living inside a [noinline] helper is still
// diagnosed once the helper has been folded into the entry point.
//
// The [noinline] is load-bearing: without it the front end inlines the helper
// itself and the prepass has nothing left to do. Its signature is all scalars
// because a function that survives to DXIL in a non-library module may not take
// or return a vector.

// The helper is gone as a function of its own...
// CHECK-NOT: define {{.*}}IndexInHelper

// ...and its dynamic index is still reported, addressed to a real ordinal rather
// than aliased onto bit 0.
// CHECK: @dx.op.waveActiveAllEqual
// CHECK: shl i32 %{{[0-9]+}}, {{[1-9][0-9]*}}
// CHECK: @dx.op.atomicBinOp.i32(i32 78
// CHECK-NOT: NuriNotInstrumentedMissingInstructionNumber

Texture2D tex[8] : register(t0);

[noinline]
float IndexInHelper(float u, float v)
{
    uint index = u * v;
    return tex[index].Load(int3(0, 0, 0)).x;
}

float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    return IndexInHelper(uv.x, uv.y);
}
