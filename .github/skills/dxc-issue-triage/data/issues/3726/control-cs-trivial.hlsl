// #3726 -- trivial compute control for the Compiler Explorer Clang pane.
//
// SKILL.md step 7: "A Clang error is not evidence until you have a control."
// Clang's DXIL backend is incomplete, so it fails on inputs that have nothing to do
// with this issue. This file is the smallest compute shader that writes an RWBuffer.
// If hlsl_clang_trunk fails on THIS with the same flags, then any failure on
// repro-cs.hlsl says nothing about #3726.
RWBuffer<float4> x0;

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    x0[tid.x] = 1;
}
