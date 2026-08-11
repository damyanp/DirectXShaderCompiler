// NEGATIVE CONTROL for issue 4763.
//
// Identical to repro.hlsl except that the resource members have been moved out
// of the cbuffer structs to file scope. This is the correct way to write the
// same program, so the predicate must NOT fire on it: it differs from the repro
// in exactly one way -- whether a resource is declared inside a cbuffer.
struct ModelData
{
    uint myInt;
};
struct ModelData2
{
    uint myInt;
};
struct ModelData3
{
    uint myInt;
};
struct ModelData4
{
    uint myInt;
};
StructuredBuffer<float3>    bufferData2;
StructuredBuffer<float4x4>  bufferData3;
Buffer<float4>              bufferData4;
cbuffer __cbModelData  { ModelData  cbModelData;  };
cbuffer __cbModelData2 { ModelData2 cbModelData2; };
cbuffer __cbModelData3 { ModelData3 cbModelData3; };
cbuffer __cbModelData4 { ModelData4 cbModelData4; };
struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};
float4 PSMain(PSInput input) : SV_Target0
{
    return input.color * cbModelData.myInt * cbModelData2.myInt * cbModelData3.myInt * cbModelData4.myInt;
}
