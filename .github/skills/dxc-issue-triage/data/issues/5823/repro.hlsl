// The entry point and target profile are needed to compile this example:
// -T ps_6_6 -E PSMain

template <int Order, typename float_t=float>
struct GaussLegendreValues;

// 2
template <typename float_t>
struct GaussLegendreValues<2,float_t>
{
    const static float_t wi[2];
    const static float_t xi[2];
};
template<typename float_t> const static float_t GaussLegendreValues<2,float_t>::wi[2] = {1.0, 1.0};
//template<typename float_t> const float_t GaussLegendreValues<2,float_t>::xi[2] = {-0.5773502691896257, 0.5773502691896257};


struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

float4 PSMain(PSInput input) : SV_Target0
{
    return input.color;// * GaussLegendreValues<2>::wi[1];
}
