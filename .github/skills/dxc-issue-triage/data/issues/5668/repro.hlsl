struct S{};
[shader("amplification")]
[numthreads(1,1,1)]
void taskMain(uint tig_0 : SV_GROUPINDEX)
{
    S s;
    DispatchMesh(1U, 1U, 1U, s);
    return;
}
