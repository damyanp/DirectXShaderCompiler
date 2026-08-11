// Default-orientation control for issue 4722: no template, no pragma, no
// qualifier, no -Zpr/-Zpc.
//
// Expect MATCH. This is what establishes -- by measurement on the build under
// test, rather than by assumption -- that DXC's default matrix orientation here
// is column-major. Without it, "the template case emits column-major" could not
// be read as "the request was dropped and the default was used".

struct Matrices {
  matrix<float, 4, 4> M;
};

cbuffer CB {
  Matrices S;
};

float4 main(float4 v : V) : SV_Target {
  return mul(S.M, v);
}
