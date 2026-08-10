// Control for issue 4501's ABSENCE clauses.
//
// Identical arguments to repro.hlsl, differing in exactly one thing: this source
// mentions the two requested instruction names in comments. Compiled with
// -fspv-debug=vulkan-with-source the shader text is embedded in the module, so
// both names appear in the disassembly and the predicate's `not_regex` clauses
// must fail.
//
// DebugBuildIdentifier
// DebugStoragePath
//
// Expect: no-match. If this control ever scores `match`, the absence clauses are
// dead regexes and every "the compiler does not emit these" result in this
// directory is worthless.

float4 g_color;

float4 main(float4 pos : SV_Position) : SV_Target {
  float4 acc = g_color;
  for (int i = 0; i < 2; ++i) {
    acc = acc * 0.5f + pos;
  }
  return acc;
}
