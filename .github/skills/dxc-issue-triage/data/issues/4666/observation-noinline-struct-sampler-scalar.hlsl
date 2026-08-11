// CONTROL for observation-noinline-struct-sampler-array.hlsl.
//
// Identical shader except the struct member is a scalar `SamplerState` rather
// than a `SamplerState[2]`. This does NOT crash -- it produces an ordinary
// diagnostic on both main-debug and v1.6.2112:
//
//   error: phi/select disallowed on pointers to local resources.
//
// so the crash in the array version is specific to the sampler *array* inside
// the aggregate, which is the same construct issue 4666 is about.
struct S { SamplerState s; };
[noinline] float f(S q, Texture2D t, float2 uv) { return t.Sample(q.s, uv).x; }
Texture2D T; SamplerState G;
float4 main(float2 uv : TEXCOORD) : SV_Target { S s; s.s = G; return f(s, T, uv); }
