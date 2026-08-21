// RUN: %dxc -enable-16bit-types -Emain -Tps_6_2 %s | %opt -S -hlsl-dxil-constantColor,constant-red=0.5,constant-green=0.25,constant-blue=0.125,constant-alpha=1 | %FileCheck %s

// A shader whose SV_Target0 is declared half writes it through the native 16-bit
// store overload, dx.op.storeOutput.f16. The pass used to materialise and visit
// only the f32 and i32 overloads, so it concluded there was nothing to override
// and returned unchanged - silently leaving the application's own colour on
// screen for every PIX visualizer that goes through this pass.

// Added override output color, built as half constants (0.5, 0.25, 0.125, 1.0):
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 0, half 0xH3800)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 1, half 0xH3400)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 2, half 0xH3000)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 3, half 0xH3C00)

// Looking for stores materialises all four storeOutput overloads on demand. The
// three this shader does not use must not survive as dead external declarations,
// which the validator rejects.
// CHECK-NOT: declare void @dx.op.storeOutput.f32
// CHECK-NOT: declare void @dx.op.storeOutput.i16
// CHECK-NOT: declare void @dx.op.storeOutput.i32

[RootSignature("")]
half4 main() : SV_Target {
    return half4(0, 0, 0, 0);
}
