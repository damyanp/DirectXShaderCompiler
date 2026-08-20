// #5072 repro: compiling a library target with -Fh and no explicit -Vn
// produces a header whose default variable name is derived from an internal
// sentinel entry-point name used for library profiles ("lib.no::entry"),
// which is not a legal C/C++ identifier.
RWStructuredBuffer<float> g_output : register(u0);

[shader("compute")]
[numthreads(1, 1, 1)]
void CSMain(uint3 dtid : SV_DispatchThreadID)
{
    g_output[dtid.x] = 1.0f;
}
