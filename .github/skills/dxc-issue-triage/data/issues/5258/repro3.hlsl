// RUN: %dxc -T lib_6_6 -HV 2021 %s
//
// Issue #5258, Example 3: a bit-field struct whose packed width (16+19+3=38
// bits) spans two uint32_t storage units, cast down to a single scalar
// `uint`. The reporter expects "some error or warning" here, since the cast
// discards half the struct's storage.

struct SomeStruct2
{
    uint32_t m1 : 16;
    uint32_t m2 : 19;
    uint32_t m3 : 3;
};

export uint SomeFunc2()
{
    SomeStruct2 s = (SomeStruct2)0;
    // Expect some error or warning when casting to uint, since SomeStruct2 is larger than one uint:
    return (uint)s;
}
