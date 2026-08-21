// RUN: %dxc -T cs_6_8 -E main -Od %s | %opt -S -hlsl-dxil-pix-shader-access-instrumentation,config=U0:0:2i0;.0;256;512. | %FileCheck %s

// Barrier() on a resource handle orders accesses to that resource. It is not
// itself an access, but it does take a handle parameter, and the access
// tracking pass treats every dx.op with a handle parameter as an access to the
// resource behind it. BarrierByMemoryHandle's DXIL memory attribute is neither
// ReadOnly nor ReadNone, so the pass fell through to its default and recorded a
// *write*: PIX showed the barrier's resource as written by a shader that only
// synchronised on it.
//
// This is the same defect as AccessTrackingLibAnnotateHandleIsNotAnAccess.hlsl
// one opcode over, but it is not confined to library targets - any shader model
// 6.8 shader calling Barrier() on a resource handle was affected.
//
// The config puts the UAVs of space 0 at slot 2 onwards, so g_out is slot 2 and
// g_rw is slot 3. A slot is three dwords - read, write, counter - so g_out's
// write dword is at byte 4 and g_rw's write dword is at byte 16.

// g_rw is only ever barriered, never accessed, so nothing may be recorded
// against it.
// CHECK-NOT: bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 16,

// The store to g_out is a genuine write and must still be recorded.
// CHECK: call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 4,

// CHECK-NOT: bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 16,

RWByteAddressBuffer g_out : register(u0);
RWTexture2D<float4> g_rw : register(u1);

[numthreads(1, 1, 1)]
void main(uint index : SV_GroupIndex)
{
    Barrier(g_rw, DEVICE_SCOPE);
    g_out.Store(0, 1);
}
