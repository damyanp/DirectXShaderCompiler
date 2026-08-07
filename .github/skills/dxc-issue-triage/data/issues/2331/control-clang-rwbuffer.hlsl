// Control for the Compiler Explorer clang pane: the smallest compute shader with the same
// resource shape and flags as case-compute.hlsl, and nothing to do with issue #2331.
// If clang fails on this too, then any clang failure on the repro is about clang's DXIL
// backend, not about the issue -- see SKILL.md step 7, measured on #1702.
RWBuffer<float4> Out : register(u0);

[numthreads(1, 1, 1)]
void MainCS(uint3 tid : SV_DispatchThreadID)
{
    Out[tid.x] = 1;
}
