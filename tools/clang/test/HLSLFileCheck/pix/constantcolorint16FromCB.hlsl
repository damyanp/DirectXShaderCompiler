// RUN: %dxc -enable-16bit-types -Emain -Tps_6_2 %s | %opt -S -hlsl-dxil-constantColor,mod-mode=1 | %FileCheck %s

// From-constant-buffer mode against a native uint16_t SV_Target0. The tools
// constant buffer is four 32-bit components; loaded values truncate to
// 16-bit integer (Trunc, not FPTrunc, since the output is integer, not
// float -- this exercises the opposite branch from constantcolorhalfFromCB.hlsl).

// CB return type is i32:
// CHECK: %dx.types.CBufRet.i32 = type { i32, i32, i32, i32 }

// Create handle:
// CHECK: %PIX_Constant_Color_CB_Handle = call %dx.types.Handle @dx.op.createHandle(i32 57, i8 2, i32 0, i32 0, i1 false)

// Load the row:
// CHECK: %PIX_Constant_Color_Value = call %dx.types.CBufRet.i32 @dx.op.cbufferLoadLegacy.i32(i32 59, %dx.types.Handle %PIX_Constant_Color_CB_Handle, i32 0)

// Extract components:
// CHECK: %PIX_Constant_Color_Value0 = extractvalue %dx.types.CBufRet.i32 %PIX_Constant_Color_Value, 0
// CHECK: %PIX_Constant_Color_Value1 = extractvalue %dx.types.CBufRet.i32 %PIX_Constant_Color_Value, 1
// CHECK: %PIX_Constant_Color_Value2 = extractvalue %dx.types.CBufRet.i32 %PIX_Constant_Color_Value, 2
// CHECK: %PIX_Constant_Color_Value3 = extractvalue %dx.types.CBufRet.i32 %PIX_Constant_Color_Value, 3

// Truncate to 16-bit integer (Trunc, the integer narrowing arm):
// CHECK: %PIX_Constant_Color_ValueNarrowed0 = trunc i32 %PIX_Constant_Color_Value0 to i16
// CHECK: %PIX_Constant_Color_ValueNarrowed1 = trunc i32 %PIX_Constant_Color_Value1 to i16
// CHECK: %PIX_Constant_Color_ValueNarrowed2 = trunc i32 %PIX_Constant_Color_Value2 to i16
// CHECK: %PIX_Constant_Color_ValueNarrowed3 = trunc i32 %PIX_Constant_Color_Value3 to i16

// Store SV_Target0:
// CHECK: call void @dx.op.storeOutput.i16(i32 5, i32 0, i32 0, i8 0, i16 %PIX_Constant_Color_ValueNarrowed0)
// CHECK: call void @dx.op.storeOutput.i16(i32 5, i32 0, i32 0, i8 1, i16 %PIX_Constant_Color_ValueNarrowed1)
// CHECK: call void @dx.op.storeOutput.i16(i32 5, i32 0, i32 0, i8 2, i16 %PIX_Constant_Color_ValueNarrowed2)
// CHECK: call void @dx.op.storeOutput.i16(i32 5, i32 0, i32 0, i8 3, i16 %PIX_Constant_Color_ValueNarrowed3)

[RootSignature("")]
uint16_t4 main() : SV_Target {
    return uint16_t4(0, 0, 0, 0);
}
