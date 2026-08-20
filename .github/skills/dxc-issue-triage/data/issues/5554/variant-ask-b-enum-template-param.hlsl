// Ask B: `enum class` used as a non-type template parameter's own declared type
// (https://godbolt.org/z/8hqrj1ezr), i.e. `template<KEK sz>` rather than `template<int sz>`.
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

template<KEK sz>
struct test {
    int operator() () {
        return partiboi[(uint)KEK::WAIT];
    }

    int partiboi[(uint)sz];
};

float4 PSMain(PSInput input) : SV_Target0
{

test<KEK::COUNT> instance;
int functorTest = instance();


float4 tab[testVar];

    return input.color * input.color;
}
