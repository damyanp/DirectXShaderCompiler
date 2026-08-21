// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-non-uniform-resource-index-instrumentation | %FileCheck %s

// Companion to NonUniformResourceIndexNoInstructionNumbers.hlsl. With the
// annotation prepass in place, the diagnostic must be addressed to the ordinal
// of the createHandle that actually performed the unqualified dynamic indexing.
// The pass encodes that ordinal as a shift, so a shift of zero means the
// diagnostic was aliased onto bit 0 rather than attributed to the instruction.
//
// The exact ordinal depends on how -dxil-annotate-with-virtual-regs numbers
// this shader, so match any non-zero shift rather than a literal. A createHandle
// whose index is computed from an interpolated input can never be the first
// numbered instruction in the function, so a zero shift here is always the bug
// and never a legitimate ordinal.

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
