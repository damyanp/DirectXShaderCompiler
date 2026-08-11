// Issue 4722, ask B and its inverse.
//
// The issue's test case says `row_major T` should be diagnosed
// ("'row_major' can only be used with a matrix type") when T is instantiated as a
// non-matrix. Here T is instantiated as float4x4 -- a matrix -- so on the issue's
// reading this must COMPILE.
//
// It does not. The diagnostic fires at template definition time, before T is
// known, so it fires for every dependent type regardless of what T turns out to
// be. Expect MATCH under match-rejects-qualifier.json.
//
// That is the same defect as repro-explicit-qualifier.hlsl seen from the other
// side: the check is not testing matrix-ness at all, it is testing whether the
// type is dependent.

template<typename T>
struct Matrices {
  row_major T M;
};

cbuffer CB {
  Matrices<float4x4> S;
};

float4 main(float4 v : V) : SV_Target {
  return mul(S.M, v);
}
