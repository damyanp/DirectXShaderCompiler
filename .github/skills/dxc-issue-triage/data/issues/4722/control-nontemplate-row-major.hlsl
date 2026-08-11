// Control for issue 4722: repro.hlsl with the template removed and nothing else
// changed. The declaration is the same matrix, the same member name, the same
// cbuffer, the same pragma.
//
// Expect NO MATCH: this one really is laid out row-major, so the predicate --
// which looks for column-major layout -- must not fire. That is what isolates the
// defect to the template-dependent path rather than to matrix orientation generally.

#pragma pack_matrix(row_major)

struct Matrices {
  matrix<float, 4, 4> M;
};

cbuffer CB {
  Matrices S;
};

float4 main(float4 v : V) : SV_Target {
  return mul(S.M, v);
}
