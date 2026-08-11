// POSITIVE CONTROL for issue 4763: a closely-related invalid construct that DXC
// DOES diagnose.
//
// The only difference from variant-cbv-scalar.hlsl is the array bound on the
// ConstantBuffer view. DXC rejects this with
//   error: object types not supported in cbuffer/tbuffer view arrays.
// (tools/clang/lib/CodeGen/CGHLSLMS.cpp, AddConstantBufferView), and the repo
// has four regression tests asserting it
// (tools/clang/test/HLSLFileCheck/hlsl/diagnostics/errors/resource-in-{cbv,cbv2,tbv,tbv2}.hlsl).
//
// This proves the diagnostic pipeline for "a resource is inside a constant
// buffer" exists and is reached, so silence on repro.hlsl is a decision about
// which constructs are checked, not a compiler that never looks.
struct ModelData2
{
    StructuredBuffer<float3> bufferData;
    uint myInt;
};
ConstantBuffer<ModelData2> cbModelData2[4];
struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};
float4 PSMain(PSInput input) : SV_Target0
{
    return input.color * cbModelData2[2].myInt;
}
