// RUN: %dxc -T lib_6_6 -HV 2021 %s
//
// Issue #5258 control for match.json. Same-subject positive control: two
// same-size, all-uint32_t structs (no bit-fields at all) casting into each
// other must succeed cleanly, proving the predicate does not fire on an
// ordinary, unquestionably-valid struct-to-struct cast.

struct SomeStructPlain {
    uint32_t m1;
    uint32_t m2;
};

struct StructWithUint2 {
    uint32_t a;
    uint32_t b;
};

StructWithUint2 cStructWithUint2;

export uint32_t SomeFuncCastingPlainStructs()
{
    SomeStructPlain bf = (SomeStructPlain)cStructWithUint2;
    return bf.m2;
}
