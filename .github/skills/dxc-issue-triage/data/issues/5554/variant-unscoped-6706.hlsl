// Ask C, unscoped-enum arm: the #6706 minimal contrast pair, unscoped half
// (https://godbolt.org/z/7rorK5qoW). Differs from variant-scoped-6706.hlsl in exactly one
// token: `enum` vs `enum class`.
template<typename T, T val>
struct integral_constant
{
    static const T value = val;
};


enum ENUM : uint32_t
{
    TRUE = 0,
    FALSE = 1,
    INVALID = 0x45
};

typedef integral_constant<ENUM,ENUM::TRUE> test_t;

[numthreads(1,1,1)]
void main()
{
}
