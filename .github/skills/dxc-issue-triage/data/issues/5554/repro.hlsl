// Primary repro for #5554: an `enum class` enumerator used as a non-type template argument
// for an exactly-typed template parameter, via a generic `integral_constant<T, T val>`
// pattern. Minimal contrast pair distilled from the issue thread's own examples
// (https://godbolt.org/z/EGaesxvE1, filed on #5554) and its duplicate #6706
// (https://godbolt.org/z/hheGKo9vx vs https://godbolt.org/z/7rorK5qoW). The scoped/unscoped
// contrast is the load-bearing part: variant-unscoped-6706.hlsl is identical except for one
// token (`enum class` -> `enum`) and is the anti-vacuity control (must NOT match).
template<typename T, T val>
struct integral_constant
{
    static const T value = val;
};


enum class ENUM : uint32_t
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
