// RUN: %dxc -E main -T ps_6_6 %s | FileCheck %s

// CHECK: define void @main

float4 main() : SV_TARGET {
  float4 arr[2] = {1, 2, 3, 4, 5, 6, 7, 8};
  arr[0][(int)float1(7)] = 9.0;
  return arr[0];
}
