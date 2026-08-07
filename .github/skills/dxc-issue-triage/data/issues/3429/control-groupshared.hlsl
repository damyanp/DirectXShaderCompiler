// Negative control for issue 3429.
//
// Same profile, same flags, same optimization level as repro.hlsl, and it uses TGSM the
// same way -- a groupshared float array plus a groupshared uint, read and written through a
// dynamic index inside a loop. What it does NOT do is let two different TGSM pointers reach
// the same use, so no phi of `float addrspace(3)*` is formed.
//
// Purpose: prove that match.json discriminates. A predicate that fired here would be firing
// on "uses groupshared memory" or on "compiles a compute shader", not on the defect.
// Expected: no-match (compiles clean, exit 0).

groupshared float thingies[6];
groupshared uint thingCounter;

[numthreads(8, 1, 1)]
void main() {
  if (thingies[thingCounter] >= 0.0) {
    for (int ix = thingCounter; ix >= 0; --ix) {
      thingies[ix] = 4.0;
    }
    ++thingCounter;
  }
}
