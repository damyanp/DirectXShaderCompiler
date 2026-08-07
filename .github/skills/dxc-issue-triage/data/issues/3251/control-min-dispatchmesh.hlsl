// Feature-presence control for #3251: the smallest amplification shader that calls DispatchMesh,
// run with the repro's exact flags. A release that predates amplification shaders rejects this
// too (feature absence -> the repro's invalid-probe is genuine); a release that compiles this
// but rejects the repro is rejecting something about the repro, and trimming it from the
// history would hide a real result.
struct smallPayload
{
    uint i;
};

[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.i = 1;
    DispatchMesh(1, 1, 1, p);
}
