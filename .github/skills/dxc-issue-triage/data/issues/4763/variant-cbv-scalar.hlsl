// VARIANT for issue 4763: the title's literal wording -- a resource placed in a
// `ConstantBuffer<T>` view rather than in a legacy `cbuffer {}` block.
//
// Differs from control-cbv-array.hlsl only by the array bound. DXC's check in
// AddConstantBufferView fires only when the view's range size is > 1, so this
// scalar form is expected to be accepted silently.
struct ModelData2
{
    StructuredBuffer<float3> bufferData;
    uint myInt;
};
ConstantBuffer<ModelData2> cbModelData2;
struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};
float4 PSMain(PSInput input) : SV_Target0
{
    return input.color * cbModelData2.myInt;
}
