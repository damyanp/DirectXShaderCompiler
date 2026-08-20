// Control for the v1.8.2405 name-collision artefact: identical to repro.hlsl except the
// template is renamed `my_integral_constant`, avoiding the (then-buggy, since-fixed by
// commit 8b18659ae / PR #6700 "Avoid adding types to default namespace") builtin
// `integral_constant` name collision that some SPIR-V-codegen-enabled builds register in the
// global namespace. If this still fails the same way, the v1.8.2405 clean result was an
// invalid probe, not a real fix.
template<typename T, T val>
struct my_integral_constant
{
    static const T value = val;
};


enum class ENUM : uint32_t
{
    TRUE = 0,
    FALSE = 1,
    INVALID = 0x45
};

typedef my_integral_constant<ENUM,ENUM::TRUE> test_t;

[numthreads(1,1,1)]
void main()
{
}
