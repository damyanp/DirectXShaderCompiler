// Control for issue 4721: a fix-it that has nothing to do with HLSL.
//
// A missing semicolon is diagnosed by inherited clang parser code, and the
// hint is an *insertion* rather than a replacement. Captured to show that the
// fix-it corpus DXC inherits is not limited to the two HLSL-specific hints in
// SemaHLSL.cpp -- so "apply fix-its" is a request about the whole diagnostic
// surface, not one diagnostic.
//
// Also serves as a negative control for match-hint.json: a fix-it for a
// different diagnostic must not satisfy a predicate anchored on the HLSL one.
float4 main() : SV_Target {
  float4 v = 1.0
  return v;
}
