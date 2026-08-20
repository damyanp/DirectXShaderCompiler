/*
Because HLSL SSBOs are nerfed compared to GLSL, we can't have
```glsl
layout() buffer readonly LineStyles
{
    float phaseShift;
    float _pad[];
} lineStyles;
```
and for every `StructuredBuffer<T> identifier;` you end up getting an equivalent of
```glsl
layout() buffer readonly Anonymous
{
    T identifier[];
};
```
*/
struct LineStyle
{
    float phaseShift;
    uint _pad[1u];
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
