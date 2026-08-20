// RUN: %dxc -T lib_6_6 -HV 2021 %s
//
// Issue #5258 self-test for match-example3.json. This compiles successfully
// (the entry point reaches DXIL, same as the real repro) but also triggers a
// genuine, unrelated diagnostic (implicit vector truncation), proving the
// not_regex "error|warning" clause can actually detect a presence rather than
// only ever observing absence.

export uint SomeFunc2SelfTestWarning()
{
    float4 v4 = float4(1, 2, 3, 4);
    float3 v3 = v4; // implicit truncation warning
    return (uint)v3.x;
}
