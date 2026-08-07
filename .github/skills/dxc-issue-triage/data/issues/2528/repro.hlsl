// microsoft/DirectXShaderCompiler#2528
// Verbatim from the issue body.
//
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 0,
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 1,
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 2,
// CHECK: call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 3,

// Should pass the rest (xyz) of SV_Position through
void main(inout float4 pos: SV_Position) {
  pos.w = 1;
}
