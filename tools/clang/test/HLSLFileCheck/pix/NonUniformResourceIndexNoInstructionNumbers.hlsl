// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -hlsl-dxil-non-uniform-resource-index-instrumentation | %FileCheck %s

// The NonUniformResourceIndex instrumentation addresses each diagnostic it
// emits by the PIX instruction ordinal that -dxil-annotate-with-virtual-regs
// attaches as metadata. This RUN line deliberately omits that prepass, so no
// createHandle carries an ordinal.
//
// The pass used to fall through with a zero-initialized ordinal and write a
// record for bit 0, which is indistinguishable from a genuine violation at
// instruction 0 and collapses every violation in the shader onto the same bit.
// It must instead leave the handle uninstrumented and report the missing
// precondition, matching the way DxilDebugInstrumentation declines to
// instrument unnumbered instructions (see DontDebugNoRegnum.hlsl).
//
// The pass writes its messages to the same stream as the -S module print, and
// writes them before the module, so the message checks come first.

// CHECK-NOT: FoundDynamicIndexingNoNuri
// CHECK: NuriNotInstrumentedMissingInstructionNumber
// CHECK-NOT: @dx.op.waveActiveAllEqual
// CHECK-NOT: @dx.op.atomicBinOp

Texture2D tex[8] : register(t0);

float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    uint index = uv.x * uv.y;
    return tex[index].Load(int3(0, 0, 0));
}
