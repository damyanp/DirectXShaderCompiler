// Scope probe for #3251: is it specific to the implicit $Globals cbuffer, or does any legacy
// cbuffer do it? Same as repro.hlsl except the global is inside an explicit `cbuffer` block.
// Run with the repro's arguments; not scored by match.json.
struct LinearSHSampleData
{
       float4 linearTerms[3];
       float4 hdrColorAO;
       float4 visibilitySH;
};

cbuffer MyCB : register(b0)
{
    LinearSHSampleData g_lhSampleData;
};

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
