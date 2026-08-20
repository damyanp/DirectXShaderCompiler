// The entry point and target profile are needed to compile this example:
// -T ps_6_6 -E PSMain
template<typename T>
struct Operator
{
    const static T identity[2];
};

template<>
const static float Operator<float>::identity[2] = {1.f,0.f};

struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

float4 PSMain(PSInput input) : SV_Target0
{
    return input.color * float32_t4(Operator<float>::identity[0],Operator<float>::identity[1],1.f,1.f);
}
