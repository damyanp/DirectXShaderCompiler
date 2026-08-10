#pragma pack_matrix(row_major)

// #4492, store direction. The issue is about loading; this measures whether the
// same byte-offset scale is used when WRITING a matrix element, because the
// store path in TranslateStructBufMatSubscript shares the same idxList.
//
// Row-major half4x4 in a 32-byte element: a[0][1] -> byte 2, a[3][3] -> byte 30.
// A doubled stride puts them at 4 and 60, i.e. a store past the end of the
// element and into the next one.
//
// Not part of match.json and not part of the verdict; recorded so the claim
// about stores is measured rather than inferred from reading the lowering code.

struct Data
{
    float16_t4x4 a;
};

RWStructuredBuffer<Data> buf : register(u0);

[numthreads(1, 1, 1)]
void testStructuredBufferMatrixLoad2()
{
    buf[0].a[0][1] = (float16_t)1.0;
    buf[0].a[3][3] = (float16_t)2.0;
}
