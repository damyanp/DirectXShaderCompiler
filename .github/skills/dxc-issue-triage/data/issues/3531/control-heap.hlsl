// Feature-presence control for issue 3531.
//
// The smallest shader that uses SM 6.6 dynamic resources at all, under the repro's exact
// profile and flags. A release that predates ResourceDescriptorHeap rejects this outright,
// which is what distinguishes "this release cannot express the feature" (invalid probe) from
// "this release compiled the repro and the symptom was or was not there".
//
// It declares no local dynamic resource, so under match.json it must score no-match: the
// anti-vacuity clause (the declaration read back out of the embedded source) fails. Its
// value is the exit status and the diagnostics, not the predicate score.

RWBuffer<float> floatRWUAV : register(u0);

static RWByteAddressBuffer DynamicBuffer = ResourceDescriptorHeap[1];
[numthreads(1, 1, 1)]
void DynamicResources()
{
    uint val = DynamicBuffer.Load(0u);
    floatRWUAV[0] = val;
}
