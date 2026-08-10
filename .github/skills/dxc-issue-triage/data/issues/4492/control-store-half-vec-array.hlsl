#pragma pack_matrix(row_major)

// Negative control for match-store.json.
//
// The same shape as store-matrix.hlsl -- same entry point, profile, flags, an
// RWStructuredBuffer whose $Element is also 32 bytes, and the same
// @dx.op.rawBufferStore.f16 instrument -- but with the half4x4 replaced by an
// array of half4 vectors, which is not the code path under test.
//
// Using the read-only control-half-vec-array.hlsl here would be worthless: it
// emits no stores at all, so it would fail the store predicate's anchor clause
// and score no-match for an instrument reason rather than a behavioural one.
// A control has to differ from the subject in exactly one way.
//
// v[0][1] -> byte 2, v[3][3] -> byte 30. Both inside the 32-byte element.
// Expected: no-match under match-store.json.

struct Data
{
    float16_t4 v[4];
};

RWStructuredBuffer<Data> buf : register(u0);

[numthreads(1, 1, 1)]
void testStructuredBufferMatrixLoad2()
{
    buf[0].v[0][1] = (float16_t)1.0;
    buf[0].v[3][3] = (float16_t)2.0;
}
