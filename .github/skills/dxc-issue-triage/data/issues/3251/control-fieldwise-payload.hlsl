// Negative control for #3251: identical to repro.hlsl -- same $Globals-backed global, same
// payload struct, same as_6_5 DispatchMesh -- except the copy is written field by field, so the
// front end emits element-wise cbuffer loads instead of one llvm.memcpy out of the cbuffer.
// That is the single difference from the repro. Must compile cleanly and must NOT match.
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
    p.lhSampleData.linearTerms[0] = g_lhSampleData.linearTerms[0];
    p.lhSampleData.linearTerms[1] = g_lhSampleData.linearTerms[1];
    p.lhSampleData.linearTerms[2] = g_lhSampleData.linearTerms[2];
    p.lhSampleData.hdrColorAO     = g_lhSampleData.hdrColorAO;
    p.lhSampleData.visibilitySH   = g_lhSampleData.visibilitySH;
    DispatchMesh(1, 1, 1, p);
}
