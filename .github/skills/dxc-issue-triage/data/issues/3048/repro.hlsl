struct A {
  float4 stuff;
};
struct B : A {
  float4 gimme() {return stuff;}
};
struct C : B {
  void dostuff() {stuff = 0;}
};
float4 f(B thing1) { // THIS IS THE PROBLEM
  return thing1.gimme();
}
float4 main() : SV_Target
{
  C thing2;
  thing2.stuff = float4(1,2,3,4);
  return f(thing2);
}
