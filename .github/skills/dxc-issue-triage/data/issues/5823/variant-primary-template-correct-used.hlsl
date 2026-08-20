// Same primary (non-specialized) class template as
// variant-primary-template-fix-test.hlsl, but (a) syntactically
// correct OOL definition (single 'const', no duplicated 'static'),
// and (b) the array is actually instantiated/used, to see whether
// the PR #8079 fix (which only suppresses codegen for the
// un-instantiated template-declaration VarDecl) also produces
// correct output for the real instantiation, and whether the
// standards-correct spelling still triggers the
// "'const' is not a valid modifier for a field" misparse seen on
// specialization members.
template<typename T>
struct MyClass {
  const static T array[2];
};

template<typename T> const T MyClass<T>::array[2] = { 1, 2 };

RWStructuredBuffer<float> outBuf;

[numthreads(1, 1, 1)]
void main() {
  outBuf[0] = MyClass<float>::array[0];
}
