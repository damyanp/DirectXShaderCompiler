struct Foo {
  int x;
  operator bool() {
    return x < 5;
  }
};

[numthreads(1, 1, 1)]
void main(uint tidx : SV_DispatchThreadId) {
  Foo A = {1};
  if (A)
    A.x += 2;
}
