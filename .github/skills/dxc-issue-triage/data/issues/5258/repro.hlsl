// RUN: %dxc -T lib_6_6 -HV 2021 %s
//
// Issue #5258, Example 1: struct-to-struct cast between a plain-uint struct
// and a bit-field struct whose total bit-field width also fits one uint32_t
// storage unit. Reported as rejected with a "cannot convert" diagnostic.

struct SomeStructWithBitfields {
    uint32_t m1 : 8;
    uint32_t m2 : 16;
    uint32_t m3 : 6;
};

struct StructWithUint {
    uint32_t u;
};

StructWithUint cStructWithUint;

export uint32_t SomeFuncCastingStructs()
{
    // error: cannot convert from 'const StructWithUint' to 'SomeStructWithBitfields'
    SomeStructWithBitfields bf = (SomeStructWithBitfields)cStructWithUint;
    return bf.m2;
}
