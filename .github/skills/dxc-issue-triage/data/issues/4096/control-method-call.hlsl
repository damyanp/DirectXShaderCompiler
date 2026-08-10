struct Foo {
  int x;
  bool asBool() {
    return x < 5;
  }
};

[numthreads(1, 1, 1)]
void main(uint tidx : SV_DispatchThreadId) {
  Foo A = {1};
  if (A.asBool())
    A.x += 2;
}
