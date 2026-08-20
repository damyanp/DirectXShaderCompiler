RWByteAddressBuffer sb : register(u0);
[numthreads(1, 1, 1)]
void main() {
  sb.Store(0, asuint(int2(123, 123))); // Okay
  sb.Store(0, asuint((123).xx)); // Boom
}
