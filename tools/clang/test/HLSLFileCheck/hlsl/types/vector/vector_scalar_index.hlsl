// RUN: not %dxc -E main -T ps_6_6 %s 2>&1 | FileCheck %s --check-prefix=INVALID
// RUN: %dxc -DVALID -E main -T ps_6_6 %s

// INVALID: error: vector element index '7' is out of bounds
// INVALID: error: vector element index '-1' is out of bounds

float4 main() : SV_TARGET {
  float4 arr[2] = {1, 2, 3, 4, 5, 6, 7, 8};
#ifdef VALID
  arr[0][(int)float1(1)] = 9.0;
#else
  arr[0][(int)float1(7)] = 9.0;
  arr[0][(int)float1(-1)] = 9.0;
#endif
  return arr[0];
}
