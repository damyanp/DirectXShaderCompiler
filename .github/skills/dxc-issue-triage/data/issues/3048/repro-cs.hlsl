struct A {
  float4 stuff;
};
struct B : A {
  float4 gimme() { return stuff; }
};
struct C : B {
  void dostuff() { stuff = 0; }
};
float4 f(B thing1) {
  return thing1.gimme();
}
RWStructuredBuffer<float4> output;

[numthreads(1, 1, 1)]
void main()
{
	C thing2;
	thing2.stuff = float4(1, 2, 3, 4);
	output[0] = f(thing2);
}
