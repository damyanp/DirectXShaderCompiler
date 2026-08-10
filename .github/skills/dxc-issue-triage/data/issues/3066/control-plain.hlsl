// Negative control for #3066: a valid shader that compiles and disassembles
// cleanly but contains none of the constructs the predicate pins.
// No resources, no ViewID dependencies on a named input, no 0.0001 constant.
// Expect: no-match. Proves the predicate is not satisfied by any successful
// compile.

float4 main() : SV_Target { return float4(1, 0, 0, 1); }
