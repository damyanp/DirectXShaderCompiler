// Ask A, with-cast arm: identical to variant-ask-a-no-cast.hlsl except both the array
// index and the template argument are explicitly cast to `uint`
// (https://godbolt.org/z/M6Kna6r7s). Reporter's own comment says this arm compiles.
struct PSInput
{
    float4 position : SV_Position;
    float4 color    : COLOR0;
};

const static int testVar = 4;

enum class KEK : uint
{
NO = 0,
WAIT=69,
COUNT=70
};

template<int sz>
struct test {
    int operator() () {
        return partiboi[(uint)KEK::WAIT];
    }

    int partiboi[sz];
};

float4 PSMain(PSInput input) : SV_Target0
{

test<(uint)KEK::COUNT> instance;
int functorTest = instance();


float4 tab[testVar];

    return input.color * input.color;
}
