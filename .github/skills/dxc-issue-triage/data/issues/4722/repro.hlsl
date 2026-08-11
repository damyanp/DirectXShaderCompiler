// Issue 4722 -- the silent face: a matrix orientation request is dropped when the
// matrix type is template-dependent.
//
// #pragma pack_matrix(row_major) asks for row-major layout. The member below is
// matrix<T, X, Y>, which is template-dependent. Nothing is diagnosed and dxc exits 0,
// so the only evidence is the emitted DXIL: the cbuffer layout says which
// orientation was actually used.
//
// Paired controls:
//   control-nontemplate-row-major.hlsl     same declaration written concretely
//   control-template-column-major.hlsl     identity control: the opposite request
//   control-nontemplate-default.hlsl       what the default orientation is here

#pragma pack_matrix(row_major)

template<typename T, int X, int Y>
struct Matrices {
  matrix<T, X, Y> M;
};

cbuffer CB {
  Matrices<float, 4, 4> S;
};

float4 main(float4 v : V) : SV_Target {
  return mul(S.M, v);
}
