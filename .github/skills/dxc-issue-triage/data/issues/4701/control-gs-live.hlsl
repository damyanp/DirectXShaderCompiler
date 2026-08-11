// CONTROL for issue 4701 -- instrument self-test.
// A groupshared array that IS read back and observed, so the allocation and the
// addrspace(3) store must legitimately survive. Declared --expect match: it proves the
// predicate's two regexes can see a groupshared global and an addrspace(3) store when one
// really is there. If this stops matching on some release, that release is unmeasurable
// under this predicate rather than clean.
RWBuffer<float> outBuf;

groupshared float a[10];

[numthreads(8,8,1)]
void main(uint gi : SV_GroupIndex) {
  a[gi % 10] = 1;
  GroupMemoryBarrierWithGroupSync();
  outBuf[gi] = a[(gi + 1) % 10];
}
