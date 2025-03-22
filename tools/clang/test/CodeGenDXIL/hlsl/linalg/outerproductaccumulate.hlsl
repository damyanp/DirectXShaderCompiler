// RUN: %dxc -T lib_6_9 %s | FileCheck %s

#include "linalg.h"

RWByteAddressBuffer RWBuf;

export void Test4(vector<half, 128> Input1, vector<half, 256> Input2) {
  using namespace dx::linalg;

  RWMatrixRef<DATA_TYPE_FLOAT16, 128, 256, MATRIX_LAYOUT_OUTER_PRODUCT_OPTIMAL>
      matrix = {RWBuf, 0, 0};

  // clang-format off
  // CHECK: call void {{.*}}__builtin_OuterProductAccumulate@{{.*}}(<128 x float> %Input1, <256 x float> %Input2, i32 0, i32 0, i32 8, i32 3)
  // clang-format on
  OuterProductAccumulate(Input1, Input2, matrix);
}
