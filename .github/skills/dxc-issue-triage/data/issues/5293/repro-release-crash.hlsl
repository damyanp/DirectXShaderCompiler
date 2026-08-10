// SECOND REPRO -- the one that makes a shipped RELEASE binary crash.
//
// This is repro.hlsl with the single local replaced by 32 locals. Nothing else differs:
// same template, same scalar `out` parameter, same assignment.
//
// Why it matters: every catalogued release is a Release build, so the assert is compiled
// out and repro.hlsl exits 0 there. The 2024-05-20 and 2026-08-10 comments both report
// Release crashes, and this file is what makes that visible without a Debug build.
// Measured on the shipped v1.9.2607 x64 dxc.exe: exit 0xC0000005 (access violation).
//
// The count is not arbitrary. With the assert compiled out, the valueless Optional is read
// anyway and the garbage index reaches scratch[...], where scratch is
// PackedVector<Value, 2, SmallBitVector> (tools/clang/lib/Analysis/UninitializedValues.cpp).
// SmallBitVector keeps its bits inline while they fit in SmallNumDataBits = 57
// (include/llvm/ADT/SmallBitVector.h), i.e. 28 two-bit entries; past that it heap-allocates
// and the out-of-bounds index becomes a wild pointer access instead of a masked shift.
// Measured on v1.9.2607: 27 locals exit 0, 28 locals exit 0, 29 locals access-violate, and
// so does every larger count tried. 32 is used here to stay clear of the boundary.
//
// Controls beside it: control-release-crash-no-template.hlsl and
// control-release-crash-inout.hlsl are the same 32-local shader with the template removed
// and with `out` changed to `inout`. Both exit 0 on the same release binary, so the crash
// is this defect and not "many locals".
template <typename R>
void test(R x, out uint result) {
    uint v1 = 1;
    uint v2 = 2;
    uint v3 = 3;
    uint v4 = 4;
    uint v5 = 5;
    uint v6 = 6;
    uint v7 = 7;
    uint v8 = 8;
    uint v9 = 9;
    uint v10 = 10;
    uint v11 = 11;
    uint v12 = 12;
    uint v13 = 13;
    uint v14 = 14;
    uint v15 = 15;
    uint v16 = 16;
    uint v17 = 17;
    uint v18 = 18;
    uint v19 = 19;
    uint v20 = 20;
    uint v21 = 21;
    uint v22 = 22;
    uint v23 = 23;
    uint v24 = 24;
    uint v25 = 25;
    uint v26 = 26;
    uint v27 = 27;
    uint v28 = 28;
    uint v29 = 29;
    uint v30 = 30;
    uint v31 = 31;
    uint v32 = 32;
    result = 10;
}

[numthreads(32, 32, 1)] void main(uint2 threadId: SV_DispatchThreadID) {
    uint x;
    test(10, x);
}
