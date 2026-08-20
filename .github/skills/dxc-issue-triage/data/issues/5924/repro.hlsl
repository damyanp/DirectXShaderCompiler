struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

template<typename float_t>
struct StyleClipper
{
    using float_t2 = vector<float_t, 2>;
    static float_t2 func(float_t t)
    {
        return t.xx;
    }
};

float4 PSMain(PSInput input) : SV_TARGET
{
	return input.color + StyleClipper<float>::func(input.color.x).x;
}
