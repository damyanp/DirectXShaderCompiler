// #4341 control -- A3: can a getter and a setter be distinguished by the
// const-ness of the implicit object parameter, as they are in C++?
//
// This is the idiom the C++ setter/getter pair uses, and it is what
// llvm-beanz's "broken behavior in DXC's overload resolution" refers to.
// DXC's own test
// tools/clang/test/HLSLFileCheck/hlsl/operator_overloading/subscript-operator.hlsl
// asserts that HLSL overload resolution "ignores the const-ness of the implicit
// object parameter", so the two overloads below should not be distinguishable.
//
// The two overloads return DIFFERENT values (9.0 vs A[ix]) so which one was
// selected is visible in the output rather than having to be inferred.

#define MAX_SIZE 100

struct MyArray {
  float4 A[MAX_SIZE];

  float4 operator[](int ix) {
    return 9.0;
  };

  float4 operator[](int ix) const {
    return A[ix];
  };
};

float4 main() : SV_Target {
  MyArray m;
  for (int i = 0; i < MAX_SIZE; i++)
    m.A[i] = 1.0;

  return m[0];
}
