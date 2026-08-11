// Flag control for issue 4722: the template case with NO source-level orientation
// request at all.
//
// Run twice:
//   plain  -> expect MATCH    (column-major default reaches the template path)
//   -Zpr   -> expect NO MATCH (the command-line flag DOES reach the template path)
//
// The -Zpr arm is what rules out "matrix orientation simply does not work through
// templates". The global flag is applied correctly; only the source-level
// qualifier/pragma is dropped.

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
