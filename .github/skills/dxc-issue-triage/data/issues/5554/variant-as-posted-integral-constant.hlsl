// Ask C (primary repro): a plain (unscoped) enum used as the value-type/value pair of a
// generic integral_constant-style template, exactly as posted on #5554
// (https://godbolt.org/z/EGaesxvE1). The scoped-enum contrast lives in variant-scoped.hlsl.
template<typename Integral, Integral val>
struct integral_constant
{
    static const Integral value = val;
};

enum Test {
    A = 0x1,
    B = 0x2,
    C = 0x4
};

using enum_const_type = integral_constant<Test,A>;

[numthreads(256,1,1)]
void main()
{
    enum_const_type a;
}
