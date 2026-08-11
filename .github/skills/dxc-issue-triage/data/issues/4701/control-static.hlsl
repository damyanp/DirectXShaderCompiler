// REFERENCE CASE for issue 4701 -- identical to repro.hlsl except `groupshared` -> `static`.
// A file-scope static array that is only ever stored to is dead for exactly the same reason.
// Expected: the array and the store are both removed. Declared --expect no-match.
static float a[10];

[numthreads(8,8,1)]
void main() {
  a[0] = 1;
}
