// Compiler Explorer source for issue 4701.
// Identical to repro.hlsl, with the one variable under test behind a preprocessor guard so
// that a second pane can compile the reference case from the same shared source. CE gives
// every pane one source, so this is how a one-variable A/B is expressed there.
// Verified locally to behave exactly like repro.hlsl (default) and control-static.hlsl
// (-DUSE_STATIC); see variant-ce-source-default-* and variant-ce-source-static-*.
#ifdef USE_STATIC
static float a[10];
#else
groupshared float a[10];
#endif

[numthreads(8,8,1)]
void main() {
  a[0] = 1;
}
