// Reproducer for #5744 (ddx_fine/ddy_fine, and derivative ops generally,
// are marked ReadNone same as ordinary side-effect-free unary ops, so
// generic LLVM "sink" code motion can move the call into a conditional
// successor block even though it was computed unconditionally and reads
// values from neighboring threads in the same quad/wave). Lanes that do not
// take the branch never execute a sunk call, so the derivative reads
// partially-uninitialized data -- this is the same shape as the issue's
// ReadAcrossDiagonal_DD case: value computed unconditionally, but only
// *used* inside one `if` arm, making it a sink candidate.
//
// This is the exact source used in microsoft/DirectXShaderCompiler#8001
// ("[SM6.9] Derivative Calls Incorrectly Sunk Into Conditional Branches",
// the scalar/SM6.6 repro at https://godbolt.org/z/PMK9EoTnK, itself
// cross-referenced from #5744's timeline as the later duplicate that
// carries the fix). `derivative` is computed once, unconditionally, from a
// per-lane value; its only use is inside the `if`, and the UAV store forces
// a real conditional branch rather than a `select`.
RWByteAddressBuffer g_Output : register(u0);

[numthreads(2, 2, 1)]
void main(uint3 DTid : SV_DispatchThreadID) {
    uint LaneIndex = WaveGetLaneIndex();
    float value = float(LaneIndex * 2);  // lane0=0, lane1=2, lane2=4, lane3=6
    float derivative = ddx(value);        // Expected: 2 (lane1 - lane0)
    if (LaneIndex == 3) {
        g_Output.Store(0, asuint(derivative));  // Actual (bug): 0
    }
}