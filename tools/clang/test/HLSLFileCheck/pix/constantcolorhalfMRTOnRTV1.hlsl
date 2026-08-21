// RUN: %dxc -enable-16bit-types -Emain -Tps_6_2 %s | %opt -S -hlsl-dxil-constantColor | %FileCheck %s

// The mirror image of constantcolorhalfMRT.hlsl: RTV0 is 32-bit and RTV1 is
// native 16-bit. This is a regression guard rather than a new-behaviour test -
// it passes both before and after 16-bit overload support was added, and exists
// to prove that teaching the pass about .f16 did not make it start overriding
// the wrong render target, or stop overriding the 32-bit one.

// Check the write to the float part was replaced (since it is RTV0):
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 0, float 1.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 1, float 1.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 2, float 1.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 3, float 1.000000e+00)

// Check color in RTV1 is unaffected (0xH0000 is half 0.0):
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 1, i32 0, i8 0, half 0xH0000)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 1, i32 0, i8 1, half 0xH0000)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 1, i32 0, i8 2, half 0xH0000)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 1, i32 0, i8 3, half 0xH0000)

// The integer overloads are materialised while searching for stores and must be
// cleaned up again.
// CHECK-NOT: declare void @dx.op.storeOutput.i16
// CHECK-NOT: declare void @dx.op.storeOutput.i32

struct RTOut
{
  float4 c : SV_Target;
  half4 h : SV_Target1;
};

[RootSignature("")]
RTOut main() {
  RTOut rtOut;
  rtOut.c = float4(0.f, 0.f, 0.f, 0.f);
  rtOut.h = half4(0, 0, 0, 0);
  return rtOut;
}
