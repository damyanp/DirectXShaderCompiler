// Negative control for #3251: identical payload copy, but the source is a *local* struct, so
// nothing points into the $Globals cbuffer and no cbuffer pointer ever reaches a memcpy user.
// Must compile cleanly and must NOT match match.json.
struct LinearSHSampleData
{
       float4 linearTerms[3];
       float4 hdrColorAO;
       float4 visibilitySH;
};

struct smallPayload
{
    LinearSHSampleData lhSampleData;
};


[numthreads(1, 1, 1)]
void main()
{
    LinearSHSampleData local = (LinearSHSampleData)0;
    smallPayload p;
    p.lhSampleData = local;
    DispatchMesh(1, 1, 1, p);
}
