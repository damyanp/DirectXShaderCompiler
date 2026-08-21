// RUN: %dxc -enable-16bit-types -Emain -Tps_6_2 %s | %opt -S -hlsl-dxil-constantColor,constant-red=8,constant-green=7,constant-blue=6,constant-alpha=5 | %FileCheck %s

// The integer counterpart of constantcolorhalf.hlsl: a native 16-bit integer
// SV_Target0 stores through dx.op.storeOutput.i16, which the pass used to ignore
// for the same reason it ignored .f16.

// Added override output color, built as i16 constants:
// CHECK: call void @dx.op.storeOutput.i16(i32 5, i32 0, i32 0, i8 0, i16 8)
// CHECK: call void @dx.op.storeOutput.i16(i32 5, i32 0, i32 0, i8 1, i16 7)
// CHECK: call void @dx.op.storeOutput.i16(i32 5, i32 0, i32 0, i8 2, i16 6)
// CHECK: call void @dx.op.storeOutput.i16(i32 5, i32 0, i32 0, i8 3, i16 5)

// The unused overloads must not be left behind as dead external declarations.
// CHECK-NOT: declare void @dx.op.storeOutput.f16
// CHECK-NOT: declare void @dx.op.storeOutput.f32
// CHECK-NOT: declare void @dx.op.storeOutput.i32

[RootSignature("")]
uint16_t4 main() : SV_Target {
    return uint16_t4(0, 0, 0, 0);
}
