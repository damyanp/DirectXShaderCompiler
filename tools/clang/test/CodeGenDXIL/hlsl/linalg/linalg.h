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
                         uint MatrixStartOffset, uint MatrixInterpretation,
                         uint M, uint K, uint Layout, bool MatrixTranspose,
                         uint MatrixStride, out vector<TYo, NUMo> OutputVector);

// dx.op.matvecmuladd
template <typename TYo, int NUMo, typename TYi, int NUMi, typename RESm,
          typename RESv>
void __builtin_MatVecMulAdd(vector<TYi, NUMi> InputVector,
                            uint InputVectorInterpretation, RESm MatrixResource,
                            uint MatrixStartOffset, uint MatrixInterpretation,
                            uint M, uint K, uint Layout, bool MatrixTranspose,
                            uint MatrixStride, RESv BiasVectorResource,
                            uint BiasVectorOffset,
                            uint BiasVectorInterpretation,
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

template <typename BUFFER, DataType DT, uint M, uint K, MatrixLayout ML,
          bool TRANSPOSE>
struct MatrixRefImpl {
  BUFFER Buffer;
  uint StartOffset;
  uint Stride;
};

template <typename BUFFER, DataType DT> struct VectorRefImpl {
  BUFFER Buffer;
  uint StartOffset;
};

//
// (RW)MatrixRef
//

template <DataType DT, uint M, uint K, MatrixLayout ML, bool TRANSPOSE = false>
using MatrixRef = MatrixRefImpl<ByteAddressBuffer, DT, M, K, ML, TRANSPOSE>;

template <DataType DT, uint M, uint K, MatrixLayout ML, bool TRANSPOSE = false>
using RWMatrixRef = MatrixRefImpl<RWByteAddressBuffer, DT, M, K, ML, TRANSPOSE>;

//
// (RW)VectorRef
//

template <DataType DT> using VectorRef = VectorRefImpl<ByteAddressBuffer, DT>;

template <DataType DT>
using RWVectorRef = VectorRefImpl<RWByteAddressBuffer, DT>;

//
// Vector
//

template <typename T, int N, DataType DT> struct Vector {
  vector<T, N> Data;
};

template <DataType DT, typename T, int N>
Vector<T, N, DT> InterpretedVector(vector<T, N> Vec) {
  Vector<T, N, DT> IV = {Vec};
  return IV;
}

#define BUFFER_HANDLE(H) (0)

//
// Mul
//

template <typename TYo, typename TYi, int NUMi, typename M_RES, DataType IV_DT,
          DataType M_DT, uint M_M, uint M_K, MatrixLayout M_LAYOUT,
          bool M_TRANSPOSE>
vector<TYo, M_M>
Mul(MatrixRefImpl<M_RES, M_DT, M_M, M_K, M_LAYOUT, M_TRANSPOSE> Matrix,
    Vector<TYi, NUMi, IV_DT> InputVector) {

  vector<TYo, M_M> OutputVector;

  details::__builtin_MatVecMul(InputVector.Data, IV_DT,
                               BUFFER_HANDLE(Matrix.Buffer), Matrix.StartOffset,
                               M_DT, M_M, M_K, M_LAYOUT, M_TRANSPOSE,
                               Matrix.Stride, /*out*/ OutputVector);

  return OutputVector;
}

//
// MulAdd
//

template <typename TYo, typename TYi, int NUMi, typename M_RES, DataType IV_DT,
          DataType M_DT, uint M_M, uint M_K, MatrixLayout M_LAYOUT,
          bool M_TRANSPOSE, typename BV_RES, DataType BV_DT>
vector<TYo, M_M>
MulAdd(MatrixRefImpl<M_RES, M_DT, M_M, M_K, M_LAYOUT, M_TRANSPOSE> Matrix,
       Vector<TYi, NUMi, IV_DT> InputVector,
       VectorRefImpl<BV_RES, BV_DT> BiasVector) {

  vector<TYo, M_M> OutputVector;

  details::__builtin_MatVecMulAdd(
      InputVector.Data, IV_DT, BUFFER_HANDLE(Matrix.Buffer), Matrix.StartOffset,
      M_DT, M_M, M_K, M_LAYOUT, M_TRANSPOSE, Matrix.Stride,
      BUFFER_HANDLE(BiasVector.Buffer), BiasVector.StartOffset, BV_DT,
      /*out*/ OutputVector);

  return OutputVector;
}

//
// OuterProductAccumulate
//

template <typename T, int M, int N, DataType M_DT, MatrixLayout M_LAYOUT>
void OuterProductAccumulate(vector<T, M> InputVector1,
                            vector<T, N> InputVector2,
                            RWMatrixRef<M_DT, M, N, M_LAYOUT, false> Matrix) {
  details::__builtin_OuterProductAccumulate(InputVector1, InputVector2,
                                            BUFFER_HANDLE(Matrix.Buffer),
                                            Matrix.StartOffset, M_DT, M_LAYOUT);
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
