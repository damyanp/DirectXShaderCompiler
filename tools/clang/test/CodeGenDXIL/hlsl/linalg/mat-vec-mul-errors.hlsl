// RUN: not %dxc -T lib_6_9 %s 2>&1 | FileCheck %s

#include "linalg.h"

ByteAddressBuffer Buf;

vector<float, 128> MixUpVectorAndMatrixArguments(vector<float, 128> Input) {
  using namespace dx::linalg;

  MatrixRef<DATA_TYPE_FLOAT16, 128, 128, MATRIX_LAYOUT_MUL_OPTIMAL>
      Matrix = {Buf, 0, 0};

  // CHECK: error: no matching function for call to 'Mul'
  // CHECK: note: candidate template ignored: could not match 'MatrixRefImpl' against 'Vector'
  return Mul<float>(InterpretedVector<DATA_TYPE_FLOAT16>(Input), Matrix);
}
