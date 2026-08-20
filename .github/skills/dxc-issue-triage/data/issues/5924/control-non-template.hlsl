// Control: same shape as repro.hlsl but the swizzled parameter's static type is
// spelled literally ("float") instead of coming from a template type parameter.
// This is exactly the workaround the reporter describes ("Changing `func(float_t t)`
// to `func(float t)`"). Expected: compiles clean, no "member reference base type ...
// is not a structure or union" diagnostic -- proving the predicate does not fire on
// an ordinary, non-dependent swizzle.
struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

struct StyleClipper
{
    using float_t2 = vector<float, 2>;
    static float_t2 func(float t)
    {
        return t.xx;
    }
};

float4 PSMain(PSInput input) : SV_TARGET
{
	return input.color + StyleClipper::func(input.color.x).x;
}
