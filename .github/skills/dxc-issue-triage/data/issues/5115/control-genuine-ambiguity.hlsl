void f(unsigned int){}
void f(int){}

float4 PSMain() : SV_TARGET
{
    // A genuinely ambiguous call even under real C++ rules: float->int and
    // float->unsigned int are both floating-integral conversions of equal
    // rank, so a correct overload resolver must reject this (unlike the
    // f(1) case in repro.hlsl, which C++ resolves to f(int) without
    // complaint).
    f(1.0f);
    return (float4)0;
}
