// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192 | %FileCheck %s

// A mesh shader that never reads its payload has no GetMeshPayload call, so the
// payload struct type is absent from the module and the expanded layout cannot be
// recovered from it. That used to suppress mesh output instrumentation entirely,
// leaving PIX with no data for the draw at all.
//
// Without the amplification shader's dispatch dimensions the pass cannot read the
// launching thread from the payload, but it can still record output: it falls back
// to flattening the group id with the dispatch arguments it was given, which
// default to 1.

// CHECK: %GroupIdX = call i32 @dx.op.groupId.i32(i32 94, i32 0)
// CHECK: %GroupIdY = call i32 @dx.op.groupId.i32(i32 94, i32 1)
// CHECK: %GroupIdZ = call i32 @dx.op.groupId.i32(i32 94, i32 2)
// CHECK: mul i32 %GroupIdY, 1
// CHECK: add i32 %GroupIdZ
// CHECK: mul i32 %GroupIdX, 1

// The output records themselves have to be there:
// CHECK: %PIX_DebugUAV_Handle = call %dx.types.Handle @dx.op.createHandleFromBinding
// CHECK: @dx.op.atomicBinOp.i32

// The amplification shader pass reports the expanded layout over the pass message
// channel and PIX forwards it as expanded-payload-size. It is absent here, so
// there is nothing to synthesize a payload access from.
// CHECK-NOT: getMeshPayload

struct PSInput
{
    float4 position : SV_POSITION;
};

struct MyPayload
{
    uint i;
};

[outputtopology("triangle")]
[numthreads(4, 1, 1)]
void MSMain(
    in payload MyPayload small,
    in uint tid : SV_GroupThreadID,
    out vertices PSInput verts[4],
    out indices uint3 triangles[2])
{
    SetMeshOutputCounts(4, 2);
    verts[tid].position = float4(0, 0, 0, 0);
    triangles[tid % 2] = uint3(0, tid + 1, tid + 2);
}
