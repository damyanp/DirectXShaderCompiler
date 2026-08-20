// From issue #4888 comment by @Keenuts (2023-01-03): the "working" restatement of the same
// idea, compiled with the same command as variant-cs-array.hlsl
// (-T cs_6_6 -E main -Od -Vd) but avoiding the intermediate array of resource *objects* --
// the dynamic index is selected first (as a plain uint), then used as the single, immediate
// index into ResourceDescriptorHeap, which is the pattern tex3d's comment says the compiler
// already supports. Positive control: must compile cleanly (--expect no-match against
// match.json) and give DXC something to succeed on with the same resource-declaration shape.
cbuffer Ids {
    int id1;
    int id2;
};

RWStructuredBuffer<float4> output;
SamplerState ss: register(s0);

[numthreads(64, 1, 1)]
void main(uint id : SV_DispatchThreadID) {
  Texture2D<float4> tex = ResourceDescriptorHeap[(int)NonUniformResourceIndex(id == 0 ? id1 : id2)];
  output[0] =  tex.Sample(ss, float2(0, 1));
}
