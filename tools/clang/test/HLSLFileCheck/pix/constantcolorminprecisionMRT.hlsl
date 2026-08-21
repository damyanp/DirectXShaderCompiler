// RUN: %dxc -Emain -Tps_6_0 %s | %opt -S -hlsl-dxil-constantColor | %FileCheck %s

// Min-precision RTV0 alongside a full-precision RTV1, at ps_6_0 with no
// -enable-16bit-types. This is the broadest-impact configuration for this
// defect - ordinary bandwidth-conscious HLSL, no opt-in flag, and supported all
// the way back to SM 6.0 - so it is a primary case rather than a variant of the
// native-16-bit tests.
//
// It is also the case that proves the pass's "only one overload writes
// SV_Target0" assumption. Both the f16 and the f32 storeOutput overloads are
// live in this module and both are scanned, but visitOutputInstructionCallers
// filters on SemanticKind::Target with GetSemanticStartIndex() == 0, so the f32
// stores (outputSigId 1) are not counted as SV_Target0 writes.

// The min16float RTV0 write is replaced. The default constant color is 1.0,
// which is 0xH3C00 as a half:
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 0, half 0xH3C00)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 1, half 0xH3C00)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 2, half 0xH3C00)
// CHECK: call void @dx.op.storeOutput.f16(i32 5, i32 0, i32 0, i8 3, half 0xH3C00)

// RTV1 is a different semantic index, so it must be left alone:
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 0, float 0.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 1, float 0.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 2, float 0.000000e+00)
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 3, float 0.000000e+00)

struct RTOut
{
  min16float4 h : SV_Target;
  float4 c : SV_Target1;
};

[RootSignature("")]
RTOut main() {
  RTOut rtOut;
  rtOut.h = min16float4(0, 0, 0, 0);
  rtOut.c = float4(0.f, 0.f, 0.f, 0.f);
  return rtOut;
}
