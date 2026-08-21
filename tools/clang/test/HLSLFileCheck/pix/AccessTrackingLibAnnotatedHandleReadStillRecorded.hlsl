// RUN: %dxc -T lib_6_6 -Od %s | %opt -S -hlsl-dxil-pix-shader-access-instrumentation,config=S0:1:1i0;U0:2:1i0;.256;512;1024. | %FileCheck %s

// Companion to AccessTrackingLibAnnotateHandleIsNotAnAccess.hlsl: the access
// tracking pass must stop recording dx.op.annotateHandle as an access, without
// losing the resource type information it harvests from the annotation.
//
// The annotation is the only place a handle's resource class is recoverable
// once createHandleFromBinding and createHandleFromHeap start producing untyped
// handles, so GetResourceFromHandle walks back through it from the operand of a
// genuine access. That is a different code path from the one that used to treat
// the annotation itself as an access, and this test pins the difference: every
// resource here is reached through an annotated handle, and every genuine
// access to one must still be recorded and typed.
//
// Offsets, with the config above (SRV space 0 at slot 1, UAV space 0 at slot 2,
// three dwords per slot, descriptor-heap records based at byte 256):
//   g_input read      slot 1, read dword    -> (1 * 3 * 4) + 0 = 12
//   g_input write     slot 1, write dword   -> (1 * 3 * 4) + 4 = 16   (must not appear)
//   g_output write    slot 2, write dword   -> (2 * 3 * 4) + 4 = 28
//   heapTexture read  descriptor 3          -> 256 + ((3 + 1) * 8) + 4 = 292
//
// The value stored for a descriptor-heap access encodes the shader kind in its
// top four bits and the ResourceAccessStyle in the next four. RayGeneration is
// 7 and SRVRead is 5, so 0x75000000 == 1962934272. It is that constant, not the
// offset, that proves the resource class came out of the annotation: a heap
// handle carries no other record of being an SRV.

// CHECK-NOT: bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 16,
// CHECK: call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 12,
// CHECK: call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 292, i32 undef, i32 1962934272,
// CHECK: call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 28,
// CHECK-NOT: bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 16,

ByteAddressBuffer g_input : register(t0);
RWByteAddressBuffer g_output : register(u0);

[shader("raygeneration")]
void RayGen()
{
    Texture2D<float4> heapTexture = ResourceDescriptorHeap[3];
    uint value = g_input.Load(0);
    value += asuint(heapTexture.Load(int3(0, 0, 0)).x);
    g_output.Store(0, value);
}
