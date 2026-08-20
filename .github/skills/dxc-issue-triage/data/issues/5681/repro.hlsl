[numthreads(1,1,1)]
void main() {
  struct T {
    uint value;
  };

  RWByteAddressBuffer b = ResourceDescriptorHeap[0];
  int original;
  InterlockedMax(b.Load<T>(0).value, 1, original);
}
