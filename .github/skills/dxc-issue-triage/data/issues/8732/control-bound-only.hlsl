// #8732 CONTROL (negative) -- repro.hlsl with the heap assignment deleted.
// Known-good input: no descriptor heap is involved at all, so match.json must
// NOT fire. Differs from repro.hlsl in exactly one line.
RWByteAddressBuffer outputBytes : register(u0);
RWTexture2D<uint> boundTex : register(u1);
[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) {
    uint original;
    RWTexture2D<uint> mixed = boundTex;
    InterlockedAdd(mixed[tid.xy], 1, original);
    outputBytes.Store(0, original);
}
