// RUN: %dxc -Tlib_6_6 %s | %opt -S -hlsl-dxil-pix-dxr-invocations-log,maxNumEntriesInLog=100 | %FileCheck %s

// Every DXR invocation atomically claims a slot in the log. The log has a fixed
// capacity, so a dispatch with more invocations than slots overflows it.
//
// The overflowing invocations used to have their slot index clamped to the last
// slot, so they all piled into it: the entry that legitimately owned that slot
// was overwritten, the last slot ended up holding whichever invocation happened
// to write it last, and nothing in the recorded data said any of that had
// happened. PIX presented a truncated log as if it were complete.
//
// The atomic counter is separate from the log and keeps counting past capacity,
// so PIX can already compare it against the capacity to detect the overflow -
// it reads both the counter and the clamped entry count. Skipping the stores
// once the log is full therefore both preserves the entries that did fit and
// leaves the overflow visible, with no change needed on the PIX side.

// CHECK: [[ENTRYINDEX:%EntryIndexResult[0-9]*]] = call i32 @dx.op.atomicBinOp.i32(i32 78,

// The bound is the entry count, not the last valid index: an index equal to the
// count is already out of range.
// CHECK: [[INRANGE:%EntryIndexIsInRange[0-9]*]] = icmp ult i32 [[ENTRYINDEX]], 100
// CHECK: br i1 [[INRANGE]]

// The offset is computed from the unclamped index, which is only reached when
// it is in range.
// CHECK: mul i32 [[ENTRYINDEX]], 52
// CHECK: call void @dx.op.bufferStore.i32
// CHECK: call void @dx.op.bufferStore.f32
// CHECK: call void @dx.op.bufferStore.f32
// CHECK: call void @dx.op.bufferStore.i32

// dx.op.binary.i32 opcode 40 is UMin, which implemented the clamp. Nothing in
// this shader uses it otherwise, so neither the call nor its declaration should
// survive - a declaration left behind with no callers fails DXIL validation.
// CHECK-NOT: @dx.op.binary.i32(i32 40
// CHECK-NOT: declare i32 @dx.op.binary.i32

struct Payload
{
    float4 color;
};

struct Attribs
{
    float2 barycentrics;
};

RaytracingAccelerationStructure scene : register(t0);
RWTexture2D<float4> output : register(u0);

[shader("raygeneration")]
void RayGen()
{
    RayDesc ray;
    ray.Origin = float3(0, 0, 0);
    ray.Direction = float3(0, 0, 1);
    ray.TMin = 0.001f;
    ray.TMax = 1000.f;
    Payload payload;
    payload.color = float4(0, 0, 0, 0);
    TraceRay(scene, RAY_FLAG_NONE, ~0, 0, 1, 0, ray, payload);
    output[DispatchRaysIndex().xy] = payload.color;
}

[shader("closesthit")]
void ClosestHit(inout Payload payload, in Attribs attribs)
{
    payload.color = float4(attribs.barycentrics, 0, 1);
}

[shader("miss")]
void Miss(inout Payload payload)
{
    payload.color = float4(1, 0, 0, 1);
}
