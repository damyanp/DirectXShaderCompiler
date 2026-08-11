// Feature-presence control for issue 4722.
//
// The smallest shader that uses HLSL 2021 templates at all, and nothing else
// under test: no matrix, no orientation request, no pragma.
//
// Its job is in the release sweep. A release that predates HLSL 2021 rejects
// every other file here before reaching the code under test, and a rejected
// compile must not be read as a clean result. If this file compiles, that
// release can express the construct the issue is about.
//
// Expect NO MATCH under match.json (it declares no matrix at all, so the
// predicate has nothing to find); its informative output is its exit status.

template<typename T>
T twice(T x) {
  return x + x;
}

float4 main(float4 v : V) : SV_Target {
  return twice<float4>(v);
}
