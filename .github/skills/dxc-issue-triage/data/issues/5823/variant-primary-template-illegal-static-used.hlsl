// Same primary (non-specialized) class template, illegal duplicated
// 'static' at the OOL definition site (as in the upstream PR #8079
// regression test), but with the array actually instantiated/used,
// to see whether the illegal-static "workaround" also rescues the
// primary-template case the way it rescues the full/explicit
// specialization case (variant-full-spec-used-array.hlsl).
template<typename T>
struct MyClass {
  const static T array[2];
};

template<typename T> const static T MyClass<T>::array[2] = { 1, 2 };

RWStructuredBuffer<float> outBuf;

[numthreads(1, 1, 1)]
void main() {
  outBuf[0] = MyClass<float>::array[0];
}
