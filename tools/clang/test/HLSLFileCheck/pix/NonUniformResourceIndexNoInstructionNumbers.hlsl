// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -hlsl-dxil-non-uniform-resource-index-instrumentation | %FileCheck %s

// This pass addresses each diagnostic by the PIX instruction ordinal.
// This RUN line omits the annotation prepass, so no createHandle carries
// an ordinal. The pass leaves the handle uninstrumented and reports the
// missing precondition. It must not create the tools UAV: checking only
// the wave/atomic calls would still pass if the UAV creator ran but no
// wave or atomic instruction were emitted, so also check the UAV resource
// name directly.
//
// This RUN line cannot also prove the root signature is unchanged: %dxc's
// FileCheck substitution disassembles the fully-serialized container, by
// which point the root signature is already a separate container part and
// no longer IR metadata, so %opt never sees it here regardless of the
// pass's behavior. That guarantee is proved instead in PixTest.cpp by
// PixTest::NonUniformResourceIndex_MissingInstructionNumberPreservesRootSignature,
// which seeds a known root signature directly on the DxilModule and
// compares it byte for byte before and after the pass runs.
//
// The pass writes its messages to the same stream as the -S module print,
// and writes them before the module, so the message checks come first.

// CHECK-NOT: FoundDynamicIndexingNoNuri
// CHECK: NuriNotInstrumentedMissingInstructionNumber
// CHECK-NOT: @dx.op.waveActiveAllEqual
// CHECK-NOT: @dx.op.atomicBinOp
// CHECK-NOT: PixUAVResource

Texture2D tex[8] : register(t0);

float4 main(float2 uv : TEXCOORD0) : SV_TARGET
{
    uint index = uv.x * uv.y;
    return tex[index].Load(int3(0, 0, 0));
}
