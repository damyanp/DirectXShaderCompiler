// Issue 4722 -- the loud face, and the shape of the issue's own test case.
//
// The issue's test case declares
//     row_major matrix<T, X, Y> RowMajor;
// inside a template and marks it as expected to COMPILE (only the non-matrix
// members carry expected-error). Today it does not compile: the orientation
// qualifier applied to a template-dependent matrix type is rejected with the
// diagnostic the issue reserves for non-matrix types.
//
// The error fires at template DEFINITION time, before any instantiation.
//
// Scored by match-rejects-qualifier.json. Paired with
// control-explicit-qualifier-nontemplate.hlsl, which is the same declaration
// spelled concretely and compiles cleanly.

template<typename T, int X, int Y>
struct Matrices {
  row_major matrix<T, X, Y> RowMajor;
};

cbuffer CB {
  Matrices<float, 4, 4> S;
};

float4 main(float4 v : V) : SV_Target {
  return mul(S.RowMajor, v);
}
