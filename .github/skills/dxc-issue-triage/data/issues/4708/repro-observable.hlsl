// Issue 4708, observable variant. This is repro.hlsl with the result actually STORED,
// so the free operator's effect is visible in generated code instead of being dead.
//
// Needed because in the reporter's original shader `result` is unused, so a compiler
// that accepts the program emits an empty main() -- which reads as "nothing happened"
// rather than as "the free operator resolved". Here the sum reaches a UAV, so a pane
// that compiles shows the arithmetic.
//
// Everything about the construct under test is unchanged: the two namespace-scope
// operator+ templates, and the use site `arr1 + 2.0f`.
template<typename T, uint32_t N>
class array
{
    T mArr[N];
    void set(const T value) {
        [unroll] for(uint i = 0 ; i < N; i++) { mArr[i] = value; }
    }
    float operator[](const uint32_t pos)
    { return mArr[pos]; }
};

template<typename T, uint32_t N>
array<T,N> operator+ (array<T,N> lhs, T rhs) {
    array<T,N> arr;
    [unroll] for(uint i = 0 ; i < N; i++) { arr.mArr[i] = lhs.mArr[i] + rhs; }
    return arr;
}
template<typename T, uint32_t N>
array<T,N> operator+ (T lhs, array<T,N> rhs) {
    array<T,N> arr;
    [unroll] for(uint i = 0 ; i < N; i++) { arr.mArr[i] = lhs + rhs.mArr[i]; }
    return arr;
}

RWStructuredBuffer<float> Out : register(u0);

[numthreads(1, 1, 1)]
void main( uint3 DTid : SV_DispatchThreadID )
{
    array<float, 3> arr1;
    arr1.set(2.0);
    array<float, 3> result = arr1 + 2.0f;
    Out[DTid.x] = result[0];
}
