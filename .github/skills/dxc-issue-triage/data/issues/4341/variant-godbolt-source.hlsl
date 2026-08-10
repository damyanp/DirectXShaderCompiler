// #4341 -- Compiler Explorer publication source.
//
// Identical to repro.hlsl except that the one line under test is behind a
// preprocessor guard, so the same shared CE source can serve both a subject
// pane and a control pane (-DCONTROL_NO_ASSIGN). CE gives every pane one
// source, and without the guard a Clang error could not be distinguished from
// Clang's incomplete HLSL support.
//
// Verified locally to behave identically to repro.hlsl in both configurations:
// see variant-godbolt-source-*.txt.

#define MAX_SIZE 100

struct MyArray {
  float4 A[MAX_SIZE];

  float4 operator[](int ix) {
    if (ix >= MAX_SIZE)
      return 0.0;
    return A[ix];
  };
};

float4 main() : SV_Target {
  MyArray m;
  for (int i = 0; i < MAX_SIZE; i++)
    m.A[i] = 1.0;

#ifndef CONTROL_NO_ASSIGN
  m[0] = 9.0;
#endif

  return m.A[0];
}
