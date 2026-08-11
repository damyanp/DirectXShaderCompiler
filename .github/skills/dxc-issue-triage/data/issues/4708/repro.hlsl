// Issue 4708: "Free operator overload" — verbatim from the issue body.
// https://github.com/microsoft/DirectXShaderCompiler/issues/4708
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

[numthreads(1, 1, 1)]
void main( uint3 DTid : SV_DispatchThreadID )
{
    array<float, 3> arr1;
    array<float, 3> arr2;
    arr1.set(2.0);
    arr2.set(2.0);
    array<float, 3> result = arr1 + 2.0f;
}
