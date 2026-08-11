// Issue 4701, verbatim from the issue body.
// A groupshared array that is only ever stored to, never loaded.
// The reporter expects both the store and the groupshared global to be removed.
groupshared float a[10];

[numthreads(8,8,1)]
void main() {
  a[0] = 1;
}
