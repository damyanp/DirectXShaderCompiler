// Negative control for microsoft/DirectXShaderCompiler#2528.
//
// Identical to repro.hlsl except that the body is empty, so no component of the
// inout signature element is modified. The issue states this case is handled
// correctly, so all four storeOutput calls must be present and match.json must
// NOT fire.  --expect no-match

void main(inout float4 pos: SV_Position) {
}
