struct Foo {
  int x;
};

[numthreads(1, 1, 1)]
void main(uint tidx : SV_DispatchThreadId) {
  Foo A = {1};
  if (A.x < 5)
    A.x += 2;
}
