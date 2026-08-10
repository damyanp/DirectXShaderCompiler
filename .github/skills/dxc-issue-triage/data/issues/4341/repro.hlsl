// #4341 -- [HLSL 2021] Setter array subscript operator overload.
//
// The struct is quoted from the issue body. The reporter's snippet is a GETTER
// (returns float4 by value); the issue asks how to write a SETTER, i.e. how to
// make `m[ix] = v;` work. That assignment appears nowhere in the thread, so the
// entry point below is agent-constructed.
//
// The two candidate behaviours are made to produce visibly DIFFERENT values:
//   A[0] is seeded with 1.0, then m[0] = 9.0 is executed, then A[0] is returned.
//     returns 9.0  -> the write landed: a setter subscript works
//     returns 1.0  -> the write was silently discarded: overload not selected
//     compile error -> the write was rejected: feature absent, diagnosed

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

  m[0] = 9.0;

  return m.A[0];
}
