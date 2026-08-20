struct VS_OUTPUT
{
    float4 position : SV_Position;
    float4 uv : TEXCOORD0;
    float4 color : VC;
};

float4 ps_main(VS_OUTPUT input) : SV_Target0
{
    return float4(0, 0, 0, 0);
}
