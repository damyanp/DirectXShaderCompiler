RWByteAddressBuffer sb : register(u0);

void f(float a) {
  sb.Store(0, a);
}

[numthreads(1, 1, 1)]
void main() {
  float b = asuint((123).x);
  f(b);
  float c = asint((123).x);
  f(c);
  float d = asfloat((123).x);
  f(d);
}
