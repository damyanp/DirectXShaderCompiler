// RUN: %dxc -T lib_6_6 -HV 2021 %s
//
// Issue #5258, Example 2, RECONSTRUCTED. The as-filed snippet
// (repro2-as-filed.hlsl) has an undeclared-variable typo that prevents it
// from compiling at all; this restates the evidently-intended statement
// `SomeStructWithEnum s = (SomeStructWithEnum)0;` while keeping everything
// else -- including the struct's first bit-field being enum-typed -- as
// posted. The reporter says this cast "only succeeds when the first bitfield
// is not an enum"; see control-example2-plain-first.hlsl for that A/B.

enum SomeEnum { Val1 };

struct SomeStructWithEnum
{
    SomeEnum m3 : 3;
};

export int SomeFuncUsingEnum()
{
    SomeStructWithEnum s = (SomeStructWithEnum)0;
    s.m3 = Val1;
    return (int)s.m3;
}
