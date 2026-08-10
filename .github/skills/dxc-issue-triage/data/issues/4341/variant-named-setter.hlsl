// #4341 control -- A4 / positive control.
//
// Two jobs:
//  (1) prove the whole pipeline reaches codegen for this struct on this profile,
//      so that a failure in repro.hlsl is attributable to the assignment rather
//      than to the struct, the profile or the flags;
//  (2) show that a *named* mutating member function is accepted and its store
//      lands, i.e. writing to A[] from inside a method is not the obstacle --
//      only the subscript-operator spelling is.
//
// Same seeded-value design as repro.hlsl: seed 1.0, write 9.0, return A[0].
// A correct compile returns 9.0.

#define MAX_SIZE 100

struct MyArray {
  float4 A[MAX_SIZE];

  float4 operator[](int ix) {
    if (ix >= MAX_SIZE)
      return 0.0;
    return A[ix];
  };

  void Set(int ix, float4 v) {
    A[ix] = v;
  };
};

float4 main() : SV_Target {
  MyArray m;
  for (int i = 0; i < MAX_SIZE; i++)
    m.A[i] = 1.0;

  m.Set(0, 9.0);

  return m.A[0];
}
