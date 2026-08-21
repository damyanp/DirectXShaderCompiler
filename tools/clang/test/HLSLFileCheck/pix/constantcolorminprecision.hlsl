// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -hlsl-dxil-constantColor,constant-red=0.5,constant-green=0.25,constant-blue=0.125,constant-alpha=1 | %FileCheck %s

// The missing 16-bit overloads were not limited to -enable-16bit-types shaders.
// A min16float SV_Target lowers to dx.op.storeOutput.f16 in ordinary
// min-precision mode too, at any shader model - note this RUN line uses neither
// -enable-16bit-types nor SM 6.2. So the visualizers were broken on plain
// min-precision shaders as well, which is a much wider blast radius than the
// native-16-bit case.

// Added override output color:
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 0, half 0xH3800)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 1, half 0xH3400)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 2, half 0xH3000)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 3, half 0xH3C00)

// CHECK-NOT: declare void @dx.op.storeOutput.f32
// CHECK-NOT: declare void @dx.op.storeOutput.i16
// CHECK-NOT: declare void @dx.op.storeOutput.i32

[RootSignature("")]
min16float4 main() : SV_Target {
    return min16float4(0, 0, 0, 0);
}
