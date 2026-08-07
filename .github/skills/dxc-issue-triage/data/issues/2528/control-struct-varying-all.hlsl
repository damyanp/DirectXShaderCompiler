// Negative control for match-varying.json (microsoft/DirectXShaderCompiler#2528).
//
// Identical to case-struct-varying.hlsl except that all four components of the
// TEXCOORD0 element are written, so nothing needs passing through. Output element
// 1 must then carry storeOutput for i8 0..3 and match-varying.json must NOT fire.
// --expect no-match
//
// It is the non-vacuous control for that predicate's absence clause: this shader
// genuinely does store output element 1 components 1/2/3.

struct V {
  float4 pos : SV_Position;
  float4 uv  : TEXCOORD0;
};

void main(inout V v) {
  v.uv = float4(1, 2, 3, 4);
}
