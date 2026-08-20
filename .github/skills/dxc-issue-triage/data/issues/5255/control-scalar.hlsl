struct InstanceDataStructType
{
    float4 data;
};

cbuffer InstanceData
{
    InstanceDataStructType mData;
};

struct VS_INPUT
{
    float3 position : POSITION;
    float4 texcoord0 : TEXCOORD0;
    float4 diffuse: COLOR0;
};

struct VS_OUTPUT
{
    float4 position : SV_Position;
    float4 uv : TEXCOORD0;
    float4 color : VC;
};

VS_OUTPUT vs_main(VS_INPUT input, uint instanceID : SV_InstanceID)
{
    VS_OUTPUT output = (VS_OUTPUT)0;
    output.position += mData.data;

    return output;
}

float4 ps_main(VS_OUTPUT input) : SV_Target0
{
    return input.color;
}
