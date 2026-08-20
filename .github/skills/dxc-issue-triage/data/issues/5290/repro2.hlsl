struct VS_APPEND {
    float4 texcoord1 : TEXCOORD1;
};

struct VS_OUTPUT
{
    float4 position : SV_Position;
    float4 uv : TEXCOORD0;
    float4 color : VC;
    VS_APPEND _append;
};

struct LayerColor
{
    float4 r;
};
struct Material
{
    LayerColor colors[4];
};

float4 ps_main(VS_OUTPUT input) : SV_Target0
{
    Material mtl = (Material)0;
    return float4(0, 0, 0, 0);
}
