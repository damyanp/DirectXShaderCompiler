// Issue 4701, consequence case: the surviving dead groupshared allocation is not cosmetic.
// 16384 floats = 65536 bytes of group shared memory, stored to once and never read --
// dead by exactly the argument in the issue. Pairs with case-budget-static.hlsl, which is
// the same dead 64 KB array declared `static` instead.
groupshared float big[16384];

[numthreads(8,8,1)]
void main() {
  big[0] = 1;
}
