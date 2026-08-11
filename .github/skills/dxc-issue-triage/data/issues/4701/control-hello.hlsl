// CONTROL for issue 4701 -- feature-presence probe.
// The smallest cs_6_0 shader that does something observable and declares no array at all.
// Every release in the catalog must compile this; if one cannot, its result on the repro is
// an invalid probe rather than a clean one. Declared --expect no-match.
RWBuffer<float> outBuf;

[numthreads(8,8,1)]
void main(uint gi : SV_GroupIndex) {
  outBuf[gi] = 1;
}
