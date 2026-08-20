// From issue #4888 comment by @Keenuts (2023-01-03): a compute-shader restatement of the
// reporter's pattern (static const array of ResourceDescriptorHeap-backed Texture2D objects,
// indexed with NonUniformResourceIndex). Command as posted:
//   ./build/bin/dxc ./repro.hlsl -T cs_6_6 -E main -Od -Vd
// Reported to fail the same way as the pixel-shader repro (DXIL path), and to crash with an
// `isa<>` assertion in include/llvm/Support/Casting.h when `-spirv` is added. Kept as a
// variant, not the primary probe: same underlying pattern, different shader stage, used to
// cross-check the DXIL failure and to drive the SPIR-V crash predicate (match-crash.json).
cbuffer Ids {
    int id1;
    int id2;
};

static const Texture2D<float4> textures[2] = {
    Texture2D<float4>(ResourceDescriptorHeap[id1]),
    Texture2D<float4>(ResourceDescriptorHeap[id2])
};

RWStructuredBuffer<float4> output;
SamplerState ss: register(s0);

[numthreads(64, 1, 1)]
void main(uint id : SV_DispatchThreadID) {
  output[0] = textures[NonUniformResourceIndex(id)].Sample(ss, float2(0, 1));
}
