// RUN: %dxc -T lib_6_9 %s | FileCheck %s

#include "linalg.h"

ByteAddressBuffer Buf;

export float4 Test1(float4 Input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 4, 4, MATRIX_LAYOUT_MUL_OPTIMAL, true> Matrix = {
      Buf, 0, 0};

  // clang-format off
  // CHECK: call void {{.*__builtin_MatVecMul@.*}}(<4 x float> %{{.+}}, i32 8, i32 0, i32 0, i32 8, i32 4, i32 4, i32 2, i1 zeroext true, i32 0, <4 x float>* nonnull dereferenceable(16) %{{.+}})
  return Mul<float>(    
      Matrix, InterpretedVector<DATA_TYPE_FLOAT16>(Input));
  // clang-format on
}

export vector<float, 8> Test2(vector<uint8_t4_packed, 6> Input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_UINT8, 8, 6 * 4, MATRIX_LAYOUT_MUL_OPTIMAL> Matrix = {
      Buf, 0, 0};

  // clang-format off
  // CHECK: call void {{.*__builtin_MatVecMul@.*}}(<6 x i32> %{{.+}}, i32 18, i32 0, i32 0, i32 19, i32 8, i32 24, i32 2, i1 zeroext false, i32 0, <8 x float>* nonnull dereferenceable(32) %{{.+}})
  // clang-format on
  return Mul<float>(Matrix,
                    InterpretedVector<DATA_TYPE_UINT8_T4_PACKED>(Input));
}
