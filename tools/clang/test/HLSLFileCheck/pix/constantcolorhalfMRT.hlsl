// RUN: %dxc -enable-16bit-types -Emain -Tps_6_2 %s | %opt -S -hlsl-dxil-constantColor | %FileCheck %s

// A shader that mixes a native 16-bit RTV0 with a 32-bit RTV1. Both storeOutput
// overloads are live in the same module, so this pins down that the pass picks
// the overload that actually writes SV_Target0 rather than the first one it
// happens to find, and that it still leaves the other render target alone.

// Check the write to the half part was replaced (since it is RTV0). The default
// constant color is 1.0, which is 0xH3C00 as a half:
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 0, half 0xH3C00)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 1, half 0xH3C00)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 2, half 0xH3C00)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 3, half 0xH3C00)

// Check color in RTV1 is unaffected:
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 0, float 0.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 1, float 0.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 2, float 0.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 3, float 0.000000e+00)

struct RTOut
{
  half4 h : SV_Target;
  float4 c : SV_Target1;
};

[RootSignature("")]
RTOut main() {
  RTOut rtOut;
  rtOut.h = half4(0, 0, 0, 0);
  rtOut.c = float4(0.f, 0.f, 0.f, 0.f);
  return rtOut;
}
