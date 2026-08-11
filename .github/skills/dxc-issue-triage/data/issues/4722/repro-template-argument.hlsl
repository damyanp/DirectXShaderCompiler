// Issue 4722, second silent shape: the orientation qualifier written on a
// TEMPLATE ARGUMENT rather than on a dependent member declaration.
//
// This is the shape the issue author's own root-cause note describes --
// "attributes getting dropped during type canonicalization". The attribute is
// spelled explicitly (not via a pragma), the code compiles with no diagnostic,
// and the emitted layout is the default.
//
// Expect MATCH under match.json.

template<typename T>
struct Matrices {
  T M;
};

cbuffer CB {
  Matrices<row_major float4x4> S;
};

float4 main(float4 v : V) : SV_Target {
  return mul(S.M, v);
}
