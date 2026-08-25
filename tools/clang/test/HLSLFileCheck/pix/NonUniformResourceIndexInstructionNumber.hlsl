// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-non-uniform-resource-index-instrumentation | %FileCheck %s

// With the annotation prepass in place, the diagnostic is addressed to
// the ordinal of the createHandle that performed the unmarked dynamic
// indexing. The pass encodes the ordinal modulo 32 as a shift amount; the
// ordinal divided by 32 is a word index, scaled by 4 to become a byte
// offset into the UAV. A shift of zero does not mean ordinal 0: ordinals
// 32 and 64 also give a shift of zero, in a different word.
//
// Match any non-zero shift rather than a literal ordinal, since the exact
// ordinal for this createHandle is fragile against unrelated compiler
// changes. This test establishes only that the shift is not zero for this
// createHandle, not which specific ordinal produced it.

// CHECK-NOT: NuriNotInstrumentedMissingInstructionNumber
// CHECK: @dx.op.waveActiveAllEqual
// CHECK: shl i32 %{{[0-9]+}}, {{[1-9][0-9]*}}
// CHECK: @dx.op.atomicBinOp.i32(i32 78

Texture2D tex[8] : register(t0);

float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    uint index = uv.x * uv.y;
    return tex[index].Load(int3(0, 0, 0));
}
