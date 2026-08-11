// Identity control for issue 4722: repro.hlsl with the OPPOSITE orientation
// requested. Everything else is identical.
//
// Expect MATCH -- and, more importantly, expect the emitted DXIL to be
// BYTE-IDENTICAL to repro.hlsl's. Two source files asking for opposite layouts
// cannot both be right, so identical output proves one request was ignored.
// That conclusion does not depend on knowing which layout is correct, which is
// why this is the decisive measurement rather than any single output reading.
//
// The byte comparison itself is in manual-case-identity.txt.

#pragma pack_matrix(column_major)

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
