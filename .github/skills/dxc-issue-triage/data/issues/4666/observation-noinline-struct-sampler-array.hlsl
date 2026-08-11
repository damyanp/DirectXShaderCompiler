// ADJACENT FINDING (not the reported symptom of issue 4666).
//
// Issue 4666 reports that a `SamplerState[2]` *parameter* is rejected, and the
// reporter states that wrapping the sampler in a struct works around it for
// DXIL. That workaround does work while the callee is inlined -- see
// control-spirv-struct-inlined.hlsl, which compiles clean to DXIL.
//
// This file is that same workaround with inlining suppressed. It does not
// produce a diagnostic: it crashes the compiler.
//   main-debug  -> 0xE0000001  "Internal compiler error: LLVM Assert"
//   release     -> 0xC0000005  "access violation ... read from address 0x0"
//
// It reproduces on v1.6.2112 -- a release that does NOT exhibit symptom A --
// so it is an older, independent defect, not part of the v1.7.2207 regression.
//
// The array is load-bearing: observation-noinline-struct-sampler-scalar.hlsl is
// the same shader with `SamplerState s;` instead of `SamplerState s[2];` and it
// produces an ordinary diagnostic instead of crashing.
struct S { SamplerState s[2]; };
[noinline] float f(S q, Texture2D t, float2 uv) { return t.Sample(q.s[0], uv).x; }
Texture2D T; SamplerState G[2];
float4 main(float2 uv : TEXCOORD) : SV_Target { S s; s.s = G; return f(s, T, uv); }
