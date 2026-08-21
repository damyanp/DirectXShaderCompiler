// RUN: %dxc -EMSMain -Tms_6_6 -enable-16bit-types %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,UAVSize=8192 | %FileCheck %s
// RUN: %dxc -EMSMain -Tms_6_6 -enable-16bit-types %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,UAVSize=8192 | %FileCheck %s -check-prefixes=NOZEROEXTENSION

// DXIL's i16 is signless, so int16_t and uint16_t mesh outputs share the one
// storeVertexOutput.i16 overload and the pass has to widen both to the 32-bit
// slot in the output record. Zero-extending unconditionally turns int16_t(-1)
// into 65535, which is what PIX's mesh output viewer then displays. Only the
// output signature still knows which of the two the element was.

// The signed output (sigId 1) is sign-extended:
// CHECK: call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %{{[^,]+}}, i32 %{{[^,]+}}, i32 undef, i32 -1, i32 undef, i32 undef, i32 undef, i8 1)
// CHECK: call void @dx.op.storeVertexOutput.i16(i32 171, i32 1, i32 0, i8 0, i16 -1, i32 %{{[^)]+}})

// The unsigned output (sigId 2) keeps zero extension:
// CHECK: call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %{{[^,]+}}, i32 %{{[^,]+}}, i32 undef, i32 7, i32 undef, i32 undef, i32 undef, i8 1)
// CHECK: call void @dx.op.storeVertexOutput.i16(i32 171, i32 2, i32 0, i8 0, i16 7, i32 %{{[^)]+}})

// A half is recorded as its raw bit pattern - it is bitcast to i16 and only the
// low 16 bits are meaningful - so that one stays zero-extended regardless of
// what the signature says. 0xBC00 is -1.0h.
// CHECK: call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %{{[^,]+}}, i32 %{{[^,]+}}, i32 undef, i32 48128, i32 undef, i32 undef, i32 undef, i8 1)
// CHECK: call void @dx.op.storeVertexOutput.f16(i32 171, i32 3, i32 0, i8 0, half 0xHBC00, i32 %{{[^)]+}})

// 65535 is the zero-extended int16_t(-1) and must appear nowhere in the module.
// NOZEROEXTENSION-NOT: i32 65535

struct PSInput
{
    float4 position : SV_POSITION;
    int16_t signedValue : SIGNEDVALUE;
    uint16_t unsignedValue : UNSIGNEDVALUE;
    half halfValue : HALFVALUE;
};

[outputtopology("triangle")]
[numthreads(3, 1, 1)]
void MSMain(
    in uint tid : SV_GroupThreadID,
    out vertices PSInput verts[3],
    out indices uint3 tris[1])
{
    SetMeshOutputCounts(3, 1);
    verts[tid].position = float4(0, 0, 0, 1);
    verts[tid].signedValue = -1;
    verts[tid].unsignedValue = 7;
    verts[tid].halfValue = -1.0h;
    if (tid == 0)
    {
        tris[0] = uint3(0, 1, 2);
    }
}
