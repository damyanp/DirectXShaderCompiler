// RUN: %dxc -T lib_6_9 %s | FileCheck %s

#include "linalg.h"

RWByteAddressBuffer RWBuf;

export void Test5(vector<half, 128> Input) {
  using namespace dx::linalg;

  // clang-format off
  // CHECK: call void {{.*}}__builtin_VectorAccumulate@{{.*}}(<128 x float> %Input, i32 0, i32 0)
  VectorAccumulate(Input, RWBuf, 0);
  // clang-format on
}