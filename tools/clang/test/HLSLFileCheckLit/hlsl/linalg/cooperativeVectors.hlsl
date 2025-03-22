// RUN: %dxc -T lib_6_9 %s | FileCheck %s

namespace dx {
namespace linalg {

// NOTE: can't be an enum class because we get this error:
//     error: non-type template argument of type 'dx::linalg::DataType' is not
//     an integral constant expression
//
enum DataType {
  DATA_TYPE_SINT16 = 2,           // ComponentType::I16
  DATA_TYPE_UINT16 = 3,           // ComponentType::U16
  DATA_TYPE_SINT32 = 4,           // ComponentType::I32
  DATA_TYPE_UINT32 = 5,           // ComponentType::U32
  DATA_TYPE_FLOAT16 = 8,          // ComponentType::F16
  DATA_TYPE_FLOAT32 = 9,          // ComponentType::F32
  DATA_TYPE_SINT8_T4_PACKED = 17, // ComponentType::PackedS8x32
  DATA_TYPE_UINT8_T4_PACKED = 18, // ComponentType::PackedU8x32
  DATA_TYPE_UINT8 = 19,           // ComponentType::U8
  DATA_TYPE_SINT8 = 20,           // ComponentType::I8
  DATA_TYPE_E4M3 =
      21, // ComponentType::F8_E4M3 (1 sign, 4 exp, 3 mantissa bits)
  DATA_TYPE_E5M2 =
      22, // ComponentType::F8_E5M2 (1 sign, 5 exp, 2 mantissa bits)
};

enum MatrixLayout {
  MATRIX_LAYOUT_ROW_MAJOR = 0,
  MATRIX_LAYOUT_COLUMN_MAJOR = 1,
  MATRIX_LAYOUT_INFERENCING_OPTIMAL = 2,
  MATRIX_LAYOUT_TRAINING_OPTIMAL = 3
};

namespace details {

template <typename BUFFER, DataType TYPE, uint M, uint K, MatrixLayout ML,
          bool TRANSPOSE>
struct MatrixRefImpl {
  BUFFER Buffer;
  uint StartOffset;
  uint Stride;

  static const DataType Type = TYPE;
  static const uint DimensionM = M;
  static const uint DimensionK = K;
  static const MatrixLayout Layout = ML;
  static const bool Transpose = TRANSPOSE;
};

template <typename BUFFER, DataType TYPE> struct VectorRefImpl {
  BUFFER Buffer;
  uint StartOffset;

  static const DataType Type = TYPE;
};

} // namespace details

//
// (RW)MatrixRef
//

template <DataType TYPE, uint M, uint K, MatrixLayout ML,
          bool TRANSPOSE = false>
struct MatrixRef
    : details::MatrixRefImpl<ByteAddressBuffer, TYPE, M, K, ML, TRANSPOSE> {};

template <DataType TYPE, uint M, uint K, MatrixLayout ML,
          bool TRANSPOSE = false>
struct RWMatrixRef
    : details::MatrixRefImpl<RWByteAddressBuffer, TYPE, M, K, ML, TRANSPOSE> {};

//
// (RW)VectorRef
//

template <DataType TYPE>
struct VectorRef : details::VectorRefImpl<ByteAddressBuffer, TYPE> {};

template <DataType TYPE>
struct RWVectorRef : details::VectorRefImpl<RWByteAddressBuffer, TYPE> {};

//
// Vector
//

template <typename T, int N, DataType TYPE> struct Vector {
  vector<T, N> Data;
  static const DataType Type = TYPE;
};

template <DataType TYPE, typename T, int N>
Vector<T, N, TYPE> InterpretedVector(vector<T, N> Vec) {
  Vector<T, N, TYPE> IV = {Vec};
  return IV;
}

//
// MulAdd
//

#define BUFFER_HANDLE(H) (0)

namespace details {
//
// As close as possible this matches dx.op.matvecmuladd. Template parameters are
// here to allow it to compile in HLSL. I expect the builtin itself will just
// take all of these parameters and can then do its own checking to make sure
// the things that need to be compile-time constants are correct etc.
//
template <typename RETURN_ELEMENT_TYPE, int RETURN_SIZE,
          typename INPUT_VECTOR_ELEMENT, int INPUT_VECTOR_N>
vector<RETURN_ELEMENT_TYPE, RETURN_SIZE> __builtin_MulAdd(
    vector<INPUT_VECTOR_ELEMENT, INPUT_VECTOR_N> InputVector,
    DataType InputVectorInterpretation,

    uint FAKE_MATRIX_BUFFER_HANDLE, // dxc doesn't like resources in exported
                                    // functions
    uint MatrixStartOffset, DataType MatrixInterpretation, uint M, uint K,
    MatrixLayout Layout, bool MatrixTranspose, uint MatrixStride,

    uint FAKE_BIAS_VECTOR_BUFFER_HNADLE, // dxc doesn't like resources in
                                         // exported functions
    uint BiasVectorOffset, DataType BiasVectorInterpretation);

} // namespace details

template <typename RESULT_TYPE, typename MATRIX, typename INPUT_VECTOR,
          typename BIAS_VECTOR>
vector<RESULT_TYPE, MATRIX::DimensionM>
MulAdd(MATRIX Matrix, INPUT_VECTOR InputVector, BIAS_VECTOR BiasVector) {

  return details::__builtin_MulAdd<RESULT_TYPE, MATRIX::DimensionM>(
      InputVector.Data, INPUT_VECTOR::Type, BUFFER_HANDLE(Matrix.Buffer),
      Matrix.StartOffset, MATRIX::Type, MATRIX::DimensionM, MATRIX::DimensionK,
      MATRIX::Layout, MATRIX::Transpose, Matrix.Stride,
      BUFFER_HANDLE(BiasVector.Buffer), BiasVector.StartOffset,
      BIAS_VECTOR::Type);
}

//
// OuterProductAccumulate
//
namespace details {
// Matching dx.op.outerproductaccumulate
template <typename T, int M, int N>
void __builtin_OuterProductAccumulate(vector<T, M> InputVector1,
                                      vector<T, N> InputVector2,
                                      uint FAKE_MATRIX_BUFFER_HANDLE,
                                      uint MatrixStartOffset,
                                      DataType MatrixInterpretation,
                                      MatrixLayout Layout);

} // namespace details

template <typename T, int M, int N, DataType TYPE, MatrixLayout ML>
void OuterProductAccumulate(vector<T, M> InputVector1,
                            vector<T, N> InputVector2,
                            RWMatrixRef<TYPE, M, N, ML, false> Matrix) {
  details::__builtin_OuterProductAccumulate(
      InputVector1, InputVector2, BUFFER_HANDLE(Matrix.Buffer),
      Matrix.StartOffset, Matrix.Type, Matrix.Layout);
}

} // namespace linalg
} // namespace dx

ByteAddressBuffer Buf;

export float4 Test1(float4 input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 4, 4, MATRIX_LAYOUT_INFERENCING_OPTIMAL> matrix =
      {Buf, 0, 0};
  VectorRef<DATA_TYPE_FLOAT16> biasVector = {Buf, 256};

  Vector<float, 4, DATA_TYPE_FLOAT16> theVector = {input};

  return MulAdd<float>(
      matrix, theVector,
      biasVector); // CHECK: %{{.+}} = call <4 x float>
                   // {{.*__builtin_MulAdd.*}}(<4 x float> %{{.+}}, i32 7, i32
                   // 0, i32 0, i32 7, i32 4, i32 4, i32 2, i1 zeroext false,
                   // i32 0, i32 0, i32 256, i32 7)
}

export float4 Test2(float4 input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 4, 4, MATRIX_LAYOUT_INFERENCING_OPTIMAL, true>
      matrix = {Buf, 0, 0};
  VectorRef<DATA_TYPE_FLOAT16> biasVector = {Buf, 256};

  Vector<float, 4, DATA_TYPE_FLOAT16> theVector = {input};

  return MulAdd<float>(
      matrix, theVector,
      biasVector); // CHECK: %{{.+}} = call <4 x float>
                   // {{.*__builtin_MulAdd.*}}(<4 x float> %{{.+}}, i32 7, i32
                   // 0, i32 0, i32 7, i32 4, i32 4, i32 2, i1 zeroext true, i32
                   // 0, i32 0, i32 256, i32 7)
}

export float4 Test3(float4 input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 4, 4, MATRIX_LAYOUT_INFERENCING_OPTIMAL, true>
      matrix = {Buf, 0, 0};
  VectorRef<DATA_TYPE_FLOAT16> biasVector = {Buf, 256};

  return MulAdd<float>(
      matrix, InterpretedVector<DATA_TYPE_FLOAT16>(input),
      biasVector); // CHECK: %{{.+}} = call <4 x float>
                   // {{.*__builtin_MulAdd.*}}(<4 x float> %{{.+}}, i32 7, i32
                   // 0, i32 0, i32 7, i32 4, i32 4, i32 2, i1 zeroext true, i32
                   // 0, i32 0, i32 256, i32 7)
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

RWByteAddressBuffer RWBuf;

export void Test4(vector<half, 128> input1, vector<half, 256> input2) {
  using namespace dx::linalg;

  RWMatrixRef<DATA_TYPE_FLOAT16, 128, 256, MATRIX_LAYOUT_TRAINING_OPTIMAL>
      matrix = {RWBuf, 0, 0};

  OuterProductAccumulate(input1, input2, matrix);
}