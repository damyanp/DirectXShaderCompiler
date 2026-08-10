// FEATURE-PRESENCE CONTROL. The smallest shader that uses an HLSL 2021 function
// template at all, under the repro's exact profile and flags (-T cs_6_6 -HV 2021).
//
// Purpose: a release that rejects repro.hlsl has to be shown to be rejecting it because
// it predates templates, not because of something unrelated in the repro. `invalid-probe`
// on both files means feature absence and the release is legitimately outside the history;
// `invalid-probe` on the repro with this file clean would mean the rejection is about the
// repro and trimming that release would hide a real result.
//
// It must NOT contain an `out` parameter or an unused local, so it does not carry the
// defect under test. Expected: compiles cleanly wherever HLSL 2021 templates exist.
RWBuffer<uint> Out : register(u0);

template <typename R>
R twice(R x) { return x + x; }

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    Out[threadId.x] = twice<uint>(2);
}
