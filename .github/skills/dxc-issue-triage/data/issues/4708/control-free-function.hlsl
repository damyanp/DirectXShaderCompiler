// Control for issue 4708. This is repro.hlsl with EXACTLY ONE difference: the free
// namespace-scope templates are named `add` instead of `operator+`, and the use site
// calls them by name instead of with operator syntax.
//
// Proves the rejection is specific to declaring an `operator` at namespace scope, and not
// to free function templates, to the class template, to passing the class by value, or to
// returning it.
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
array<T,N> add (array<T,N> lhs, T rhs) {
    array<T,N> arr;
    [unroll] for(uint i = 0 ; i < N; i++) { arr.mArr[i] = lhs.mArr[i] + rhs; }
    return arr;
}
template<typename T, uint32_t N>
array<T,N> add (T lhs, array<T,N> rhs) {
    array<T,N> arr;
    [unroll] for(uint i = 0 ; i < N; i++) { arr.mArr[i] = lhs + rhs.mArr[i]; }
    return arr;
}

[numthreads(1, 1, 1)]
void main( uint3 DTid : SV_DispatchThreadID )
{
    array<float, 3> arr1;
    array<float, 3> arr2;
    arr1.set(2.0);
    arr2.set(2.0);
    array<float, 3> result = add(arr1, 2.0f);
}
