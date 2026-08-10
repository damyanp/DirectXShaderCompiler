// #4341 control -- the reporter's own claim: "A getter works like this".
//
// Identical struct to repro.hlsl; the only difference is that the subscript is
// READ instead of written. Seeded value is 1.0, so a working getter returns 1.0
// and a working codegen is visible in the output.
//
// This is also the negative control for match.json: it is the same construct,
// on the same profile and flags, differing from the repro in exactly one way
// (read vs write), and the predicate must NOT fire on it.

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

  return m[0];
}
