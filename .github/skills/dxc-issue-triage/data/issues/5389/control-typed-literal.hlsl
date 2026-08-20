RWByteAddressBuffer sb : register(u0);
[numthreads(1, 1, 1)]
void main() {
  sb.Store(0, asuint(int2(123, 123))); // Okay -- explicitly int32-typed literal, no bare swizzle
}
