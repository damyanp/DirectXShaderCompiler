// RUN: %dxc -EASMain -Tas_6_6 %s | %opt -S -hlsl-dxil-PIX-add-tid-to-as-payload,dispatchArgY=1,dispatchArgZ=1 | %FileCheck %s -check-prefixes=AMPLIFICATION
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,dispatchArgY=1,dispatchArgZ=1,UAVSize=8192,expanded-payload-size=28,expanded-payload-offset=16 | %FileCheck %s -check-prefixes=MESH

// D3D12 requires only that an amplification shader and the mesh shader it
// dispatches declare the same payload *size*. It says nothing about the field
// layout, and the two structs here are deliberately laid out differently: the
// amplification shader's uint4 is four 4-byte-aligned dwords, while the mesh
// shader's uint64_t forces 8-byte alignment. Both declare 16 bytes, so the pair
// is legal.
//
// The amplification shader pass appends its three disambiguation dwords after
// the last field of *its* struct - at byte 16, for a total of 28 - and reports
// both numbers so PIX can forward them to the mesh shader pass. Expanding the
// mesh shader's own struct instead lands the appended dwords at byte 12 for a
// total of 24, which is a different payload size and a different layout: D3D
// refuses to create the PSO, and if it did, the mesh shader would read the
// disambiguation values out of the wrong bytes.

// The offset and size the mesh shader RUN line above is given are exactly what
// the amplification shader pass reports here.
// AMPLIFICATION: ExpandedPayloadSize:28
// AMPLIFICATION: ExpandedPayloadAppendedFieldsOffset:16
// AMPLIFICATION: %PIX_AS2MS_Expanded_Type = type { [4 x i32], i32, i32, i32 }

// The mesh shader's own i64 gives its struct an alignment of 8, so an unpacked
// struct can only ever have a size that is a multiple of 8 and could never
// reach 28. A packed struct plus explicit dword padding is the only way to
// place the appended values at byte 16 and end the struct at byte 28 while
// leaving the mesh shader's own fields at bytes 0 and 8 where its own payload
// reads expect them.
// MESH: %PIX_AS2MS_Expanded_Type = type <{ i64, i32, [1 x i32], i32, i32, i32 }>

// The three appended values follow the padding, at element indices 3, 4 and 5.
// Deriving them from the mesh shader's own field count would read indices 2, 3
// and 4 - the padding and the first two appended dwords.
// MESH: [[PAYLOAD:%[0-9]+]] = call %PIX_AS2MS_Expanded_Type* @dx.op.getMeshPayload.PIX_AS2MS_Expanded_Type(i32 170)
// MESH: getelementptr %PIX_AS2MS_Expanded_Type, %PIX_AS2MS_Expanded_Type* [[PAYLOAD]], i32 0, i32 3
// MESH: getelementptr %PIX_AS2MS_Expanded_Type, %PIX_AS2MS_Expanded_Type* [[PAYLOAD]], i32 0, i32 4
// MESH: getelementptr %PIX_AS2MS_Expanded_Type, %PIX_AS2MS_Expanded_Type* [[PAYLOAD]], i32 0, i32 5

// The mesh shader's own field keeps element index 1, so its payload read is
// unaffected by the expansion.
// MESH: getelementptr inbounds %PIX_AS2MS_Expanded_Type, %PIX_AS2MS_Expanded_Type* [[PAYLOAD]], i32 0, i32 1

// And the declared payload size - the last field of the mesh shader's entry
// properties - has to be the amplification shader's 28, not 24.
// MESH: = !{{{![0-9]+}}, i32 3, i32 1, i32 2, i32 28}

struct MismatchedLayoutPayloadAmplification
{
    uint4 values;
};

struct MismatchedLayoutPayloadMesh
{
    uint64_t alignmentAnchor;
    uint xOffsetSelector;
};

struct PSInput
{
    float4 position : SV_POSITION;
    uint selector : SELECTOR;
};

[numthreads(3, 1, 1)]
void ASMain(uint gid : SV_GroupID, uint tid : SV_GroupThreadID)
{
    MismatchedLayoutPayloadAmplification payload;
    payload.values = uint4(0, 0, tid, 0);
    DispatchMesh(1, 1, 1, payload);
}

[outputtopology("triangle")]
[numthreads(3, 1, 1)]
void MSMain(
    in uint tid : SV_GroupThreadID,
    in payload MismatchedLayoutPayloadMesh pld,
    out vertices PSInput verts[3],
    out indices uint3 tris[1])
{
    SetMeshOutputCounts(3, 1);
    verts[tid].position = float4(0, 0, 0, 1);
    verts[tid].selector = 100 + pld.xOffsetSelector;
    if (tid == 0)
    {
        tris[0] = uint3(0, 1, 2);
    }
}
