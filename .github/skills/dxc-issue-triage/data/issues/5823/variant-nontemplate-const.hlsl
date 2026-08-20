

struct Foo
{
    const static float32_t2 someConstant;
};

const float32_t2 Foo::someConstant = {1.f,0.f};

struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

float4 PSMain(PSInput input) : SV_Target0
{
    return input.color * float32_t4(Foo::someConstant.r,Foo::someConstant.g,1.f,1.f);
}
