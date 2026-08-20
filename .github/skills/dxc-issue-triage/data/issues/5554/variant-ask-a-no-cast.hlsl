// Ask A, no-cast arm: scoped enum used directly as an array index and as a template
// argument where the template parameter is `int` -- no explicit cast anywhere
// (https://godbolt.org/z/Pxd1zacr7). Contrast with variant-ask-a-with-cast.hlsl.
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
        return partiboi[KEK::WAIT];
    }

    int partiboi[sz];
};

float4 PSMain(PSInput input) : SV_Target0
{

test<KEK::COUNT> instance;
int functorTest = instance();


float4 tab[testVar];

    return input.color * input.color;
}
