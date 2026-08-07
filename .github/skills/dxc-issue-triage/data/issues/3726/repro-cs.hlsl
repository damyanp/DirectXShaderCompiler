// #3726 -- compute-shader restating of repro.hlsl, for the Compiler Explorer pane.
//
// Why it exists: Clang's DXIL backend cannot lower a pixel shader writing SV_Target
// (SKILL.md step 7), and the issue's repro is exactly that, so a Clang pane on
// repro.hlsl would be full of noise about the stage rather than about the issue.
// Compute is the stage all three compilers can answer on. Reduced to one RWBuffer
// because that is the resource type Clang's HLSL support is furthest along on --
// the construct under test is `out`-parameter assignment of a global resource, which
// is not specific to Texture2D.
//
// Verified before adoption: DXC reproduces the SAME back-end error on this file that
// it does on repro.hlsl, and -fcgl is equally silent on it (variant-cs-dxil-*.txt and
// variant-cs-fcgl-*.txt). repro.hlsl remains the stage-accurate local evidence.
RWBuffer<float4> r0;
RWBuffer<float4> x0;

void getResource(out RWBuffer<float4> a0)
{
    a0 = r0;
}

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    getResource(x0);
    x0[tid.x] = 1;
}
