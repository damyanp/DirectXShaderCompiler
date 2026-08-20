// RUN: %dxc -T lib_6_6 -HV 2021 %s
//
// Issue #5258, Example 2, VERBATIM AS FILED. This does not compile as posted:
// `SomeStructWithEnums = (SomeStructWithEnum)0;` has no type and no declared
// variable name (`SomeStructWithEnums` is not declared anywhere), and the
// following line references an undeclared `s`. Kept here only to document
// that the snippet needs reconstruction before it can be run; see repro2.hlsl
// for the reconstructed version actually probed.

enum SomeEnum { Val1 };

struct SomeStructWithEnum
{
    // Uncommenting the uint32_t field makes the cast ok somehow...
    //uint32_t m1 : 16;
    SomeEnum m3 : 3;
};

export int SomeFuncUsingEnum()
{
    // This cast only succeeds when the first bitfield is not an enum.
    // Uncommenting the uint32_t field gets past taht, but then there's a
    // crash due to issue #5257
    SomeStructWithEnums = (SomeStructWithEnum)0;
    s.m3 = Val1;
    return (int)s.m3;
}
