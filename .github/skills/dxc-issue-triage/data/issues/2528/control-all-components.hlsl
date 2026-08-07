// Negative control for microsoft/DirectXShaderCompiler#2528.
//
// Identical to repro.hlsl except that all four components of the inout signature
// element are written, so nothing needs passing through. All four storeOutput
// calls must be present and match.json must NOT fire.  --expect no-match
//
// This control specifically guards the absence clause: the shader genuinely does
// write output element 0 component 0, so "not_contains i8 0" cannot be satisfied
// vacuously here.

void main(inout float4 pos: SV_Position) {
  pos = float4(1, 2, 3, 4);
}
