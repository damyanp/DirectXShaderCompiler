// #4341 control -- A2: can a *reference-returning* subscript operator be declared?
//
// pow2clk's answer in the thread is "not currently possible due to lack of
// reference support in HLSL". This is the C++ spelling of a setter subscript.
// Same struct as repro.hlsl, same seeded-value design, only the operator's
// return type differs.

#define MAX_SIZE 100

struct MyArray {
  float4 A[MAX_SIZE];

  float4 &operator[](int ix) {
    return A[ix];
  };
};

float4 main() : SV_Target {
  MyArray m;
  for (int i = 0; i < MAX_SIZE; i++)
    m.A[i] = 1.0;

  m[0] = 9.0;

  return m.A[0];
}
