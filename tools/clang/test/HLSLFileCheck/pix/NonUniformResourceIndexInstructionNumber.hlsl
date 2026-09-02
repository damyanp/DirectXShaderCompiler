// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-non-uniform-resource-index-instrumentation | %FileCheck %s

// With the annotation prepass in place, the diagnostic is addressed to
// the ordinal of the createHandle that performed the unmarked dynamic
// indexing, encoded as a shift within a 32-bit word. A shift of zero
// does not mean instruction 0: ordinals 32 and 64 also give a zero
// shift, in a different word. This test establishes only that the
// shift is not zero.

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
