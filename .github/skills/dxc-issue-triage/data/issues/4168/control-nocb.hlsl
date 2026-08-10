// #4168 anti-vacuity control: the same chain over a library with NO cbuffer.
//
// SKILL.md: "The same clause is also vacuously true on a shader that never
// mentions the symbol". `Num Variables: 0` would be satisfied for free by any
// dump with no constant buffer in it, so the predicate's CB0 anchor has to be
// shown to fail on exactly that input. This shader is otherwise identical in
// shape to repro.hlsl -- exported function, pixel entry point, same signature
// -- and differs only in having no cbuffer for its values to come from.

export float4 xform(float4 v) {
  return v * 2.0f;
}

[shader("pixel")]
float4 main(float4 pos : TEXCOORD0) : SV_Target {
  return xform(pos);
}
