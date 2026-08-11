// Control for issue 4721: the repro with DXC's own suggested fix applied by
// hand -- `a && b` replaced by the exact text DXC prints under the caret.
// Line count and layout deliberately match repro.hlsl so the two captures are
// directly comparable.
//
// If this compiles clean, the hint DXC computes is a complete and correct fix,
// and the only thing missing is a way to apply it automatically.
//
//
//
float4 main(float4 a : A, float4 b : B) : SV_Target {
  bool4 mask = and(a, b);
  return float4(mask);
}
