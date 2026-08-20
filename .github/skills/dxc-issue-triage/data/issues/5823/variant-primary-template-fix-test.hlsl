// Exact reproduction of the regression test added by PR #8079
// (tools/clang/test/CodeGenSPIRV/template.static.var.split.hlsl),
// used here to confirm the fix's scope: primary (non-specialized)
// class template, illegal duplicated 'static' at the OOL definition,
// array unused.
template<typename T>
struct MyClass {
  const static T array[2];
};

template<typename T> const static T MyClass<T>::array[2] = { 1, 2 };

[numthreads(1, 1, 1)]
void main() {
}
