#pragma pack_matrix(row_major)

// Minimal restatement of #4492's issue body, for a legible shared repro.
//
// The body's snippet is
//     struct Data { float16_t4x4 a; };
//     StructuredBuffer<Data> buf : register(t1);
//     float16_t2 b = buf.a[0].xy;
// "This loads elements a[0][0] and a[0][2], not a[0][1] as expected."
//
// pack_matrix(row_major) matches the reporter's attached shader (1-mat.hlsl).
// a[0].xy is the reporter's exact case. a[3].zw is added because it is the last
// two scalars of the 32-byte element: correct offsets are 28 and 30, so a doubled
// stride puts them at 56 and 60, past the end of the element and therefore
// unambiguously wrong rather than merely different.
//
// Row-major half4x4, element (row r, col c) -> byte (r*4 + c)*2.
//   a[0].x = a[0][0] -> 0    a[0].y = a[0][1] -> 2
//   a[3].z = a[3][2] -> 28   a[3].w = a[3][3] -> 30
// Correct: rawBufferLoad.f16 elementOffsets 0, 2, 28, 30.

struct Data
{
    float16_t4x4 a;
};

StructuredBuffer<Data> buf : register(t1);
RWStructuredBuffer<float4> result : register(u0);

[numthreads(1, 1, 1)]
void testStructuredBufferMatrixLoad2()
{
    float16_t2 b = buf[0].a[0].xy;
    float16_t2 c = buf[0].a[3].zw;
    result[0] = float4(b.x, b.y, c.x, c.y);
}
