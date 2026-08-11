// The entry point and target profile are needed to compile this example:
// -T ps_6_6 -E PSMain -Fh test.h test.hlsl
struct ModelData // Size: 4 Bytes
{
    uint myInt; // Offset: 0 Bytes
};
struct ModelData2 // Size: 16 Bytes
{
    StructuredBuffer<float3> bufferData;
    uint myInt; // Offset: 12 Bytes
};
struct ModelData3 // Size: 68 Bytes
{
    StructuredBuffer<float4x4> bufferData;
    uint myInt; // Offset: 64 Bytes
};
struct ModelData4 // Size: 4 Bytes
{
    Buffer<float4> bufferData;
    uint myInt; // Offset: 0 Bytes
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
    return input.color * cbModelData.myInt * cbModelData2.myInt * cbModelData3.myInt * cbModelData4.myInt;
}
