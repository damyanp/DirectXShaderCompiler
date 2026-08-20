struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

cbuffer Ids {
    int id1;
    int id2;
};

static const Texture2D<float4> textures[2] = {
    Texture2D<float4>(ResourceDescriptorHeap[id1]),
    Texture2D<float4>(ResourceDescriptorHeap[id2])
};

SamplerState ss: register(s0);

float4 PSMain(PSInput input) : SV_Target0
{
    float4 sample = textures[NonUniformResourceIndex(int(input.color.x))].Sample(ss, float2(0, 1));
    return sample;
}
