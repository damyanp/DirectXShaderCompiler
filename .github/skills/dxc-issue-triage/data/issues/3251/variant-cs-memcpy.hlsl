// Scope probe for #3251: is the missing HLOpcodeGroup::NotHL case reachable without an
// amplification shader at all? Same shape as the repro -- a whole-struct copy whose SOURCE is
// the $Globals cbuffer -- but the destination is an RWStructuredBuffer element and the stage is
// plain cs_6_0. If this also traps in TranslateCBAddressUserLegacy, the defect is about
// "llvm.memcpy out of a cbuffer", not about DispatchMesh payloads.
// Run with -T cs_6_0 -E main (see variant-cs-memcpy-main-debug.txt); not scored by match.json.
struct LinearSHSampleData
{
       float4 linearTerms[3];
       float4 hdrColorAO;
       float4 visibilitySH;
} g_lhSampleData;

RWStructuredBuffer<LinearSHSampleData> outBuf;

[numthreads(1, 1, 1)]
void main()
{
    outBuf[0] = g_lhSampleData;
}
