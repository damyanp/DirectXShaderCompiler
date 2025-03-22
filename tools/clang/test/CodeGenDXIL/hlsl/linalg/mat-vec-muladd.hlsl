// RUN: %dxc -T lib_6_9 %s | FileCheck %s

#include "linalg.h"

ByteAddressBuffer Buf;

export float4 Test1(float4 input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 4, 4, MATRIX_LAYOUT_INFERENCING_OPTIMAL> matrix =
      {Buf, 0, 0};
  VectorRef<DATA_TYPE_FLOAT16> biasVector = {Buf, 256};

  Vector<float, 4, DATA_TYPE_FLOAT16> theVector = {input};

  // clang-format off
  // CHECK: call void {{.*__builtin_MulAdd@.*}}(<4 x float> %{{.+}}, i32 8, i32 0, i32 0, i32 8, i32 4, i32 4, i32 2, i1 zeroext false, i32 0, i32 0, i32 256, i32 8, <4 x float>* nonnull dereferenceable(16) %{{.+}})
  return MulAdd<float>(
      matrix, theVector,
      biasVector);
  // clang-format on
}

export float4 Test2(float4 input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 4, 4, MATRIX_LAYOUT_INFERENCING_OPTIMAL, true>
      matrix = {Buf, 0, 0};
  VectorRef<DATA_TYPE_FLOAT16> biasVector = {Buf, 256};

  Vector<float, 4, DATA_TYPE_FLOAT16> theVector = {input};

  // clang-format off
  return MulAdd<float>(
      matrix, theVector,
      biasVector); // CHECK: call void {{.*__builtin_MulAdd@.*}}(<4 x float> %{{.+}}, i32 8, i32 0, i32 0, i32 8, i32 4, i32 4, i32 2, i1 zeroext true, i32 0, i32 0, i32 256, i32 8, <4 x float>* nonnull dereferenceable(16) %{{.+}})
  // clang-format on
}

export float4 Test3(float4 input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 4, 4, MATRIX_LAYOUT_INFERENCING_OPTIMAL, true>
      matrix = {Buf, 0, 0};
  VectorRef<DATA_TYPE_FLOAT16> biasVector = {Buf, 256};

  // clang-format off
  // CHECK: call void {{.*__builtin_MulAdd@.*}}(<4 x float> %{{.+}}, i32 8, i32 0, i32 0, i32 8, i32 4, i32 4, i32 2, i1 zeroext true, i32 0, i32 0, i32 256, i32 8, <4 x float>* nonnull dereferenceable(16) %{{.+}}) 
  return MulAdd<float>(
      matrix, InterpretedVector<DATA_TYPE_FLOAT16>(input),
      biasVector);
  // clang-format on
}

namespace ProposalExample {

ByteAddressBuffer model;

vector<float, 3> ApplyNeuralMaterial(vector<half, 8> inputVector) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_E4M3, 32, 8, MATRIX_LAYOUT_INFERENCING_OPTIMAL> matrix0 =
      {model, 0, 0};

  VectorRef<DATA_TYPE_FLOAT16> biasVector0 = {model, 1024};

  MatrixRef<DATA_TYPE_E4M3, 32, 32, MATRIX_LAYOUT_INFERENCING_OPTIMAL> matrix1 =
      {model, 2048, 0};

  VectorRef<DATA_TYPE_FLOAT16> biasVector1 = {model, 3072};

  MatrixRef<DATA_TYPE_E4M3, 3, 32, MATRIX_LAYOUT_INFERENCING_OPTIMAL> matrix2 =
      {model, 4096, 0};

  VectorRef<DATA_TYPE_FLOAT16> biasVector2 = {model, 5120};

  vector<half, 32> layer0 = MulAdd<half>(
      matrix0, InterpretedVector<DATA_TYPE_E4M3>(inputVector), biasVector0);
  layer0 = max(layer0, 0);

  vector<half, 32> layer1 = MulAdd<half>(
      matrix1, InterpretedVector<DATA_TYPE_E4M3>(layer0), biasVector1);
  layer1 = max(layer1, 0);

  vector<float, 3> output = MulAdd<float>(
      matrix2, InterpretedVector<DATA_TYPE_E4M3>(layer1), biasVector2);
  output = exp(output);

  return output;
}

} // namespace ProposalExample
