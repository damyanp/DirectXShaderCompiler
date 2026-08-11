// CONTROL for issue 4701 -- the same dead array, but function-local.
// SROA + DSE should remove it entirely. Declared --expect no-match.

[numthreads(8,8,1)]
void main() {
  float a[10];
  a[0] = 1;
}
