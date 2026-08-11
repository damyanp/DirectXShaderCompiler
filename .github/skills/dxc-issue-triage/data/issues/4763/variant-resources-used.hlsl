// VARIANT for issue 4763: repro.hlsl with the cbuffer-resident resources
// actually read, so they survive dead-code elimination.
//
// repro.hlsl never uses its buffers, so they are dropped and nothing about them
// reaches the resource-binding table. This variant answers "what actually lands
// in the emitted container" when they are used.
struct ModelData
{
    uint myInt;
};
struct ModelData2
{
    StructuredBuffer<float3> bufferData;
    uint myInt;
};
struct ModelData3
{
    StructuredBuffer<float4x4> bufferData;
    uint myInt;
};
struct ModelData4
{
    Buffer<float4> bufferData;
    uint myInt;
};
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
    float3 a = cbModelData2.bufferData[0];
    float4x4 b = cbModelData3.bufferData[1];
    float4 c = cbModelData4.bufferData[2];
    return input.color * cbModelData.myInt * a.x * b._11 * c.y;
}
