// #2952 aborted-walk control: a non-library profile.
//
// Run with `-T cs_6_0`. A compute container has no RDAT part and no
// ID3D12LibraryReflection, so the harness stops with a WALK-INCOMPLETE marker
// and prints no RESULT line at all. The predicate must not match: SKILL.md's
// repeated finding is that a probe which never reached the code under test can
// otherwise score as a textbook reproduction, and this control is what proves
// it cannot here.
//
// Needs `run --args`, because the profile changes and `cmd.txt`'s lib_6_3
// cannot be reused.
//
// Expected: no-match.

RWBuffer<float4> Output : register(u0);

[numthreads(8, 1, 1)] void main(uint3 tid
                                : SV_DispatchThreadID) {
  Output[tid.x] = float4(tid, 1.0f);
}
