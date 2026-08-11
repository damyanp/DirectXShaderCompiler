// Compiler Explorer presentation for issue 4722.
//
// Both members are declared under the ONE pragma at the top of this file, and
// they differ in exactly one way: the first goes through a template, the second
// does not. Everything else -- element type, dimensions, member name, the
// cbuffer they live in -- is the same.
//
// This file exists only to make the difference readable in one pane. The
// measured evidence is repro.hlsl and its controls, which vary one thing at a
// time; see manual-case-identity.txt.

#pragma pack_matrix(row_major)

template<typename T, int X, int Y>
struct ThroughTemplate {
  matrix<T, X, Y> M;
};

struct Directly {
  matrix<float, 4, 4> M;
};

cbuffer CB {
  ThroughTemplate<float, 4, 4> A;
  Directly                     B;
};

float4 main(float4 v : V) : SV_Target {
  return mul(A.M, v) + mul(B.M, v);
}
