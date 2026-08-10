// #4492 minimal case, column-major (DXC's default packing -- no pragma).
//
// Companion to minimal-matrix.hlsl, which is the same shader under
// #pragma pack_matrix(row_major). Keeping both shows the defect is a uniform
// doubling of the scalar byte stride and not a row/column-major mix-up: every
// offset in each packing is exactly 2x the correct one for that packing.
//
// Column-major half4x4, element (row r, col c) -> byte (c*4 + r)*2.
//   a[0].x = a[0][0] -> 0    a[0].y = a[0][1] -> 8
//   a[3].z = a[3][2] -> 22   a[3].w = a[3][3] -> 30
// Correct: 0, 8, 22, 30 (all inside the 32-byte element).

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
