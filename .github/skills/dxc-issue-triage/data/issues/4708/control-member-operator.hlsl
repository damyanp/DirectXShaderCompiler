// Control for issue 4708. This is repro.hlsl with EXACTLY ONE difference: the two free
// (namespace-scope) `operator+` templates are replaced by a single MEMBER `operator+`.
// The class, the profile, the flags and the use site `arr1 + 2.0f` are unchanged.
//
// Two jobs:
//   1. negative control for match.json -- a valid shader the predicate must not fire on;
//   2. per-release feature-presence control -- a release that cannot compile this cannot
//      express class templates or member operator overloading at all, so its rejection of
//      repro.hlsl says nothing about NON-member operator overloading and the probe is
//      unmeasurable rather than a reproduction.
template<typename T, uint32_t N>
class array
{
    T mArr[N];
    void set(const T value) {
        [unroll] for(uint i = 0 ; i < N; i++) { mArr[i] = value; }
    }
    float operator[](const uint32_t pos)
    { return mArr[pos]; }

    array<T,N> operator+ (T rhs) {
        array<T,N> arr;
        [unroll] for(uint i = 0 ; i < N; i++) { arr.mArr[i] = mArr[i] + rhs; }
        return arr;
    }
};

[numthreads(1, 1, 1)]
void main( uint3 DTid : SV_DispatchThreadID )
{
    array<float, 3> arr1;
    array<float, 3> arr2;
    arr1.set(2.0);
    arr2.set(2.0);
    array<float, 3> result = arr1 + 2.0f;
}
