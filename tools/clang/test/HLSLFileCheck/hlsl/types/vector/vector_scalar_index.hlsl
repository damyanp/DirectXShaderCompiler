// RUN: not %dxc -E main -T ps_6_6 %s 2>&1 | FileCheck %s

// CHECK: error: vector element index '7' is out of bounds

float4 main() : SV_TARGET {
  float4 arr[2] = {1, 2, 3, 4, 5, 6, 7, 8};
  arr[0][(int)float1(7)] = 9.0;
  return arr[0];
}
