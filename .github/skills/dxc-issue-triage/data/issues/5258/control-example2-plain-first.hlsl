// RUN: %dxc -T lib_6_6 -HV 2021 %s
//
// Issue #5258, Example 2 control. Same as repro2.hlsl except a plain
// uint32_t bit-field now precedes the enum bit-field, matching the
// reporter's claim that "uncommenting the uint32_t field" changes the
// cast's behaviour. This is the A/B half of the same-subject comparison the
// issue asks for -- not an independent bug.

enum SomeEnum { Val1 };

struct SomeStructWithEnum
{
    uint32_t m1 : 16;
    SomeEnum m3 : 3;
};

export int SomeFuncUsingEnum()
{
    SomeStructWithEnum s = (SomeStructWithEnum)0;
    s.m3 = Val1;
    return (int)s.m3;
}
