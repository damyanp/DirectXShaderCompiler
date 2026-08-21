// RUN: %dxc -T lib_6_6 -Od %s | %opt -S -hlsl-dxil-pix-shader-access-instrumentation,config=S0:1:1i0;U0:2:1i0;.0;0;0. | %FileCheck %s

// dx.op.annotateHandle attaches type information to a handle. It is not a
// memory operation, but it does take a handle parameter, and the access
// tracking pass treats every dx.op with a handle parameter as an access to the
// resource behind that handle. On a library target the annotated handle comes
// from createHandleForLib, which the pass can resolve back to a resource, so
// the annotation produced a record of its own - and, because annotateHandle is
// ReadNone rather than ReadOnly, the pass fell through to its default and made
// it a *write* record. Read-only SRVs, CBVs, samplers and acceleration
// structures in DXR shaders were all reported to PIX as written.
//
// g_untouched below is only ever passed to GetDimensions, which the pass
// deliberately skips, so the annotation is the resource's only instrumentable
// dx.op use. Nothing at all should be recorded against it.
//
// The config above puts the SRV of space 0 at slot 1 and the UAV of space 0 at
// slot 2. A slot is three dwords - read, write, counter - so g_untouched's read
// dword is at byte 12 and its write dword at byte 16, and g_output's write
// dword is at byte 28.

// CHECK-NOT: bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 12,
// CHECK-NOT: bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 16,

// The store to g_output is a genuine access and must still be recorded:
// CHECK: call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 28,

// CHECK-NOT: bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 12,
// CHECK-NOT: bufferStore.i32(i32 69, %dx.types.Handle {{.*}}, i32 16,

Texture2D<float4> g_untouched : register(t0);
RWByteAddressBuffer g_output : register(u0);

[shader("raygeneration")]
void RayGen()
{
    uint width, height;
    g_untouched.GetDimensions(width, height);
    g_output.Store(0, width + height);
}
