// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,UAVSize=8192 | %FileCheck %s

// The pass looks the EmitIndices overload up unconditionally so it can
// instrument every emitIndices call, and OP::GetOpFunc materialises the
// declaration on demand. A mesh shader that emits no indices at all - like this
// one, which has no "out indices" parameter - is therefore left with an
// external declaration that nothing calls, and the DXIL validator rejects that:
// "External function 'dx.op.emitIndices' is unused."
//
// The four storeVertexOutput overloads are looked up the same way and have been
// erased when unused since the pass was written; EmitIndices was simply missed.

// CHECK-NOT: @dx.op.emitIndices

// The vertex outputs are still instrumented, so this is not just an
// instrumentation-did-nothing result:
// CHECK: %PIX_DebugUAV_Handle = call %dx.types.Handle @dx.op.createHandleFromBinding
// CHECK: call void @dx.op.bufferStore.i32
// CHECK: call void @dx.op.storeVertexOutput.f32

// The unused vertex-output overloads are erased too, and so is EmitIndices:
// CHECK-NOT: @dx.op.emitIndices
// CHECK-NOT: declare void @dx.op.storeVertexOutput.i16
// CHECK-NOT: declare void @dx.op.storeVertexOutput.i32
// CHECK-NOT: declare void @dx.op.storeVertexOutput.f16

struct PSInput
{
    float4 position : SV_POSITION;
};

[outputtopology("triangle")]
[numthreads(4, 1, 1)]
void MSMain(
    in uint tid : SV_GroupThreadID,
    out vertices PSInput verts[4])
{
    SetMeshOutputCounts(4, 0);
    verts[tid].position = float4(0, 0, 0, 0);
}
