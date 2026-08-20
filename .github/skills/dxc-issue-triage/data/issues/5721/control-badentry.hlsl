// control-badentry.hlsl (#5721) -- negative control for match.json.
//
// Same shape as repro.hlsl but the compute entry point is named
// `notmain`, while pdb5721-harness.cpp always links with a hardcoded
// entry name of "main". IDxcLinker::Link is therefore expected to fail
// ("Cannot find definition of function main") before ever reaching the
// QueryInterface / HasOutput / GetOutput calls the predicate looks for --
// so neither of match.json's two required substrings appears, and the
// `all_of` predicate must score no-match. This proves the predicate does
// not manufacture a match out of an unrelated early failure; it fires
// only on the specific documented absence.

RWStructuredBuffer<float> g_Out : register(u0);

[shader("compute")]
[numthreads(1, 1, 1)]
void notmain(uint3 tid : SV_DispatchThreadID) {
  float v = (float)tid.x;
  v = v * 2.0 + 1.0;
  g_Out[tid.x] = v;
}
