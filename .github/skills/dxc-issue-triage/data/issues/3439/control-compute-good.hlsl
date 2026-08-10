// TRANSFORMATION CONTROL for case-compute-restatement.hlsl. Identical shape,
// but the declared overload is defined, so nothing is left external. If the
// compute restatement is a faithful transformation, this must compile cleanly
// -- otherwise the restatement itself is the subject and the issue is not
// (SKILL.md step 7).
RWBuffer<int> Out;

int CallMeMaybe(float, bool);

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
   Out[tid.x] = CallMeMaybe((float)tid.x, false);
}

int CallMeMaybe(float f, bool b) {
    return b ? 3 : (int)f;
}
