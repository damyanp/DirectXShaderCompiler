// RUN: %dxc -enable-16bit-types -Emain -Tps_6_2 %s | %opt -S -hlsl-dxil-constantColor,mod-mode=1 | %FileCheck %s

// From-constant-buffer mode against a native 16-bit SV_Target0. The tools
// constant buffer deliberately stays four 32-bit components wide - that is the
// layout PIX uploads - so the loaded components are narrowed to the store's own
// type instead of the cbuffer being reshaped.

// Check that the CB return type has been added, still as f32:
// CHECK: %dx.types.CBufRet.f32 = type { float, float, float, float }

// Look for call to create handle:
// CHECK: %PIX_Constant_Color_CB_Handle = call %dx.types.Handle @dx.op.createHandle(i32 57, i8 2, i32 0, i32 0, i1 false)

// Look for call to read from CB:
// CHECK: %PIX_Constant_Color_Value = call %dx.types.CBufRet.f32 @dx.op.cbufferLoadLegacy.f32(i32 59, %dx.types.Handle %PIX_Constant_Color_CB_Handle, i32 0)

// Calls to load elements:
// CHECK: %PIX_Constant_Color_Value0 = extractvalue %dx.types.CBufRet.f32 %PIX_Constant_Color_Value, 0
// CHECK: %PIX_Constant_Color_Value1 = extractvalue %dx.types.CBufRet.f32 %PIX_Constant_Color_Value, 1
// CHECK: %PIX_Constant_Color_Value2 = extractvalue %dx.types.CBufRet.f32 %PIX_Constant_Color_Value, 2
// CHECK: %PIX_Constant_Color_Value3 = extractvalue %dx.types.CBufRet.f32 %PIX_Constant_Color_Value, 3

// Each component is narrowed to half so that it type-checks against the f16 store:
// CHECK: %PIX_Constant_Color_ValueNarrowed0 = fptrunc float %PIX_Constant_Color_Value0 to half
// CHECK: %PIX_Constant_Color_ValueNarrowed1 = fptrunc float %PIX_Constant_Color_Value1 to half
// CHECK: %PIX_Constant_Color_ValueNarrowed2 = fptrunc float %PIX_Constant_Color_Value2 to half
// CHECK: %PIX_Constant_Color_ValueNarrowed3 = fptrunc float %PIX_Constant_Color_Value3 to half

// Check that the store-output has been modified:
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 0, half %PIX_Constant_Color_ValueNarrowed0)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 1, half %PIX_Constant_Color_ValueNarrowed1)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 2, half %PIX_Constant_Color_ValueNarrowed2)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 3, half %PIX_Constant_Color_ValueNarrowed3)

[RootSignature("")]
half4 main() : SV_Target {
    return half4(0, 0, 0, 0);
}
