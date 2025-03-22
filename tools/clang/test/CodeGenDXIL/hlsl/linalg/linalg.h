//
// Header for linear algebra APIs.
//
// This needs to find a proper home!
//

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
  DATA_TYPE_E4M3 = 21,            // ComponentType::F8_E4M3
                                  // (1 sign, 4 exp, 3 mantissa bits)
  DATA_TYPE_E5M2 = 22,            // ComponentType::F8_E5M2
                                  // (1 sign, 5 exp, 2 mantissa bits)
};

enum MatrixLayout {
  MATRIX_LAYOUT_ROW_MAJOR = 0,
  MATRIX_LAYOUT_COLUMN_MAJOR = 1,
  MATRIX_LAYOUT_INFERENCING_OPTIMAL = 2,
  MATRIX_LAYOUT_TRAINING_OPTIMAL = 3
};

//
// Builtins
//
//
// As close as possible these match the DXIL operations. Template parameters are
// here to allow it to compile in HLSL. I expect the builtin itself will just
// take all of these parameters and can then do its own checking to make sure
// the things that need to be compile-time constants are correct etc.
//
// Fake buffer handles are used because DXC does not allow resource types in
// exported functions.

namespace details {
// dx.op.matvecmul
template <typename TYo, int NUMo, typename TYi, int NUMi, typename RES>
void __builtin_MatVecMul(vector<TYi, NUMi> InputVector,
                   uint InputVectorInterpretation, RES MatrixResource,
                   uint MatrixStartOffset, uint MatrixInterpretation, uint M,
                   uint K, uint Layout, bool MatrixTranspose, uint MatrixStride,
                   out vector<TYo, NUMo> OutputVector);

// dx.op.matvecmuladd
template <typename TYo, int NUMo, typename TYi, int NUMi, typename RESm,
          typename RESv>
void __builtin_MatVecMulAdd(vector<TYi, NUMi> InputVector,
                      uint InputVectorInterpretation, RESm MatrixResource,
                      uint MatrixStartOffset, uint MatrixInterpretation, uint M,
                      uint K, uint Layout, bool MatrixTranspose,
                      uint MatrixStride, RESv BiasVectorResource,
                      uint BiasVectorOffset, uint BiasVectorInterpretation,
                      out vector<TYo, NUMo> OutputVector);

// dx.op.outerproductaccumulate
template <typename TY, int M, int N, typename RES>
void __builtin_OuterProductAccumulate(
    vector<TY, M> InputVector1, vector<TY, N> InputVector2, RES MatrixResource,
    uint MatrixStartOffset, DataType MatrixInterpretation, MatrixLayout Layout);

// dx.op.vectoraccumulate
template <typename TY, int NUM, typename RES>
void __builtin_VectorAccumulate(vector<TY, NUM> InputVector,
                                RES OutputArrayResource,
                                uint OutputArrayOffset);

} // namespace details

namespace details {

template <typename BUFFER, DataType TY, uint M, uint K, MatrixLayout ML,
          bool TRANSPOSE>
struct MatrixRefImpl {
  BUFFER Buffer;
  uint StartOffset;
  uint Stride;

  static const DataType Type = TY;
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

#define BUFFER_HANDLE(H) (0)

//
// Mul
//

#define APPROACH 1

#if APPROACH == 0
template <typename TYo, typename MATRIX, typename INPUT_VECTOR>
vector<TYo, MATRIX::DimensionM> Mul(MATRIX Matrix, INPUT_VECTOR InputVector) {

  vector<TYo, MATRIX::DimensionM> OutputVector;

  details::__builtin_MatVecMul<TYo, MATRIX::DimensionM>(
      InputVector.Data, INPUT_VECTOR::Type, BUFFER_HANDLE(Matrix.Buffer),
      Matrix.StartOffset, MATRIX::Type, MATRIX::DimensionM, MATRIX::DimensionK,
      MATRIX::Layout, MATRIX::Transpose, Matrix.Stride, /*out*/ OutputVector);

  return OutputVector;
}
#elif APPROACH == 1

template <typename TYo, typename TYi, int NUMi, typename RES, DataType V_TYPE,
          DataType M_TYPE, uint M, uint K, MatrixLayout M_LAYOUT,
          bool M_TRANSPOSE>
vector<TYo, M>
Mul(details::MatrixRefImpl<RES, M_TYPE, M, K, M_LAYOUT, M_TRANSPOSE> Matrix,
    Vector<TYi, NUMi, V_TYPE> InputVector) {

  vector<TYo, M> OutputVector;

  details::__builtin_MatVecMul(InputVector.Data, V_TYPE, BUFFER_HANDLE(Matrix.Buffer),
                         Matrix.StartOffset, M_TYPE, M, K, M_LAYOUT,
                         M_TRANSPOSE, Matrix.Stride, /*out*/ OutputVector);

  return OutputVector;
}
#endif

//
// MulAdd
//

template <typename RESULT_TYPE, typename MATRIX, typename INPUT_VECTOR,
          typename BIAS_VECTOR>
vector<RESULT_TYPE, MATRIX::DimensionM>
MulAdd(MATRIX Matrix, INPUT_VECTOR InputVector, BIAS_VECTOR BiasVector) {
  vector<RESULT_TYPE, MATRIX::DimensionM> OutputVector;

  details::__builtin_MatVecMulAdd<RESULT_TYPE, MATRIX::DimensionM>(
      InputVector.Data, INPUT_VECTOR::Type, BUFFER_HANDLE(Matrix.Buffer),
      Matrix.StartOffset, MATRIX::Type, MATRIX::DimensionM, MATRIX::DimensionK,
      MATRIX::Layout, MATRIX::Transpose, Matrix.Stride,
      BUFFER_HANDLE(BiasVector.Buffer), BiasVector.StartOffset,
      BIAS_VECTOR::Type, /*out*/ OutputVector);

  return OutputVector;
}

//
// OuterProductAccumulate
//

template <typename T, int M, int N, DataType TYPE, MatrixLayout ML>
void OuterProductAccumulate(vector<T, M> InputVector1,
                            vector<T, N> InputVector2,
                            RWMatrixRef<TYPE, M, N, ML, false> Matrix) {
  details::__builtin_OuterProductAccumulate(
      InputVector1, InputVector2, BUFFER_HANDLE(Matrix.Buffer),
      Matrix.StartOffset, Matrix.Type, Matrix.Layout);
}

//
// VectorAccumulate
//

template <typename T, int N>
void VectorAccumulate(vector<T, N> InputVector, RWByteAddressBuffer Buffer,
                      uint Offset) {
  details::__builtin_VectorAccumulate(InputVector, BUFFER_HANDLE(Buffer),
                                      Offset);
}

} // namespace linalg
} // namespace dx
