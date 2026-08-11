// Issue 4701, consequence case: the `static` half of the pair.
// Byte-identical to case-budget-groupshared.hlsl except for the storage class, so the two
// differ in exactly one way. Same 64 KB dead array, same single dead store.
static float big[16384];

[numthreads(8,8,1)]
void main() {
  big[0] = 1;
}
