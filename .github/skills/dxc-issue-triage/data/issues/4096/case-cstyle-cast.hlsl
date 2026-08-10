// Agent-constructed. NOT the reporter's shader.
//
// The reporter's repro cannot say WHICH conversion the compiler chose: with
// `Foo A = {1}`, the operator body (`x < 5`) and HLSL's flat conversion
// (`bool(x)`) both yield true, and the shader has no observable anyway.
//
// Here the two disagree and the answer is a stored constant:
//   operator honoured  ->  x > 5 is false for x == 1  ->  stores 222
//   flat conversion    ->  bool(1) is true            ->  stores 111
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
  Out[tidx] = (bool)A ? 111 : 222;
}
