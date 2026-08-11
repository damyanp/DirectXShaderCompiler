// Positive / instrument control for issue 4722: no template, column-major
// requested explicitly.
//
// Expect MATCH. This proves the predicate can see genuine column-major layout in
// a shader where column-major is what was asked for -- i.e. the predicate is
// reading the orientation and not merely reacting to the presence of a template.

#pragma pack_matrix(column_major)

struct Matrices {
  matrix<float, 4, 4> M;
};

cbuffer CB {
  Matrices S;
};

float4 main(float4 v : V) : SV_Target {
  return mul(S.M, v);
}
