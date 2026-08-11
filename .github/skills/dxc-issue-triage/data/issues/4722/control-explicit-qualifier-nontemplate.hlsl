// Control for issue 4722's loud face: repro-explicit-qualifier.hlsl with the
// template removed and nothing else changed.
//
// Expect NO MATCH under match-rejects-qualifier.json: the same qualifier on the
// same matrix type is accepted, and the shader compiles. This is what makes the
// rejection above a template-path defect rather than a general refusal to accept
// `row_major` on a matrix.

struct Matrices {
  row_major matrix<float, 4, 4> RowMajor;
};

cbuffer CB {
  Matrices S;
};

float4 main(float4 v : V) : SV_Target {
  return mul(S.RowMajor, v);
}
