// Negative control for #3066: does not compile (missing semicolon), so dxc
// emits a plain syntax error and no disassembly at all. Expect: no-match.
// This is the guard demanded by the "an absence predicate is satisfied for
// free by a compile that never got started" rule -- every clause of match.json
// must fail on an empty listing. A syntax error is used deliberately in
// preference to an undeclared identifier: the latter is one of the runner's
// feature-absence markers and classifies as invalid-probe instead.

float4 main() : SV_Target {
  return float4(0.0001, 0, 0, 1)
}
