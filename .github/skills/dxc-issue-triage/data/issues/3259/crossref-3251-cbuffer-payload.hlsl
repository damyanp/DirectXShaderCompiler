// Collation crossover probe for microsoft/DirectXShaderCompiler#3259.
//
// NOT #3259's repro. This is the repro from #3251, verbatim from that issue's
// body -- the "other AS related issue" @damyanp's 2024 comment on #3259 points
// at. Filed by the same reporter one day earlier, with the same profile and the
// same DispatchMesh(1,1,1,p) shape.
//
// The difference under test: this payload contains NO HLSL object type, so
// GetLoweredUDT does NOT return nullptr and the null-type path #3259 is about
// is never entered. Captured so that "related, not duplicates" is measured
// rather than asserted -- see notes.md.
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
