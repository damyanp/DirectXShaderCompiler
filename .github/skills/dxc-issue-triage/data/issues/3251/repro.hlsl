// #3251 -- verbatim from the issue body (2020-11-11).
// A global struct lands in the implicit $Globals legacy cbuffer; copying it whole into the
// amplification-shader payload is emitted as one llvm.memcpy out of that cbuffer, and
// TranslateCBAddressUserLegacy has no case for a NotHL call user.
struct LinearSHSampleData
{
       float4 linearTerms[3];
       float4 hdrColorAO;
       float4 visibilitySH;
} g_lhSampleData;

struct smallPayload
{
    LinearSHSampleData lhSampleData;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.lhSampleData = g_lhSampleData;
    DispatchMesh(1, 1, 1, p);
}
