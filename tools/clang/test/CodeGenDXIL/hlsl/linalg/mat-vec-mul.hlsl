// RUN: %dxc -T lib_6_9 %s | FileCheck %s

#include "linalg.h"

ByteAddressBuffer Buf;


export float4 Test4(float4 input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 4, 4, MATRIX_LAYOUT_MUL_OPTIMAL, true>
      matrix = {Buf, 0, 0};

  // clang-format off
  // CHECK: call void {{.*__builtin_MatVecMul@.*}}(<4 x float> %{{.+}}, i32 8, i32 0, i32 0, i32 8, i32 4, i32 4, i32 2, i1 zeroext true, i32 0, <4 x float>* nonnull dereferenceable(16) %{{.+}})
  return Mul<float>(    
      matrix, InterpretedVector<DATA_TYPE_FLOAT16>(input));
  // clang-format on
}


