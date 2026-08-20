struct LineStyle
{
    float phaseShift;
    uint _pad[2u];
};
StructuredBuffer<LineStyle> lineStyles : register(t1);


struct PSInput
{
    float4 position : SV_Position;
};

float4 main(PSInput input) : SV_TARGET
{
    return float(lineStyles[45]._pad).xxxx;
}