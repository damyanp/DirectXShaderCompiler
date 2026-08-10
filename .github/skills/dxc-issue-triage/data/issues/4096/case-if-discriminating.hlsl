// Agent-constructed. NOT the reporter's shader.
//
// The reporter's construct (`if (A)`) with an observable attached, so that a
// compiler which ACCEPTS it can be asked which conversion it used:
//   operator honoured  ->  x > 5 is false for x == 1  ->  stores 222
//   flat conversion    ->  bool(1) is true            ->  stores 111
//
// Every DXC that can compile HLSL 2021 rejects this outright, which is the
// issue. It exists for the comparison compiler, which does not.
struct Foo {
  int x;
  operator bool() {
    return x > 5;
  }
};

RWBuffer<uint> Out : register(u0);

[numthreads(1, 1, 1)]
void main(uint tidx : SV_DispatchThreadId) {
  Foo A = {1};
  if (A)
    Out[tidx] = 111;
  else
    Out[tidx] = 222;
}
