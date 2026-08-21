// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=16,expanded-payload-offset=4 | %FileCheck %s -check-prefixes=EXACTFIT
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=32,expanded-payload-offset=4 | %FileCheck %s -check-prefixes=TAILPADDING
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=12,expanded-payload-offset=0 | %FileCheck %s -check-prefixes=EMPTYPAYLOAD
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=28,expanded-payload-offset=16 | %FileCheck %s -check-prefixes=MISMATCHEDLAYOUT
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=16384,expanded-payload-offset=16368 | %FileCheck %s -check-prefixes=MAXPAYLOAD

// This mesh shader declares a payload but never reads it, so the module has no
// GetMeshPayload call and no payload struct type to expand. The pass instead
// synthesizes a type from the size and offset the amplification shader pass
// reported, which is the only input it has. The synthesized type has to match
// the amplification shader's declared size exactly, because D3D refuses to
// create the PSO when the two stages disagree.
//
// The shape of the mesh shader's own payload struct is irrelevant on this path;
// only the reported size and offset matter, so they are what this test varies.
// The original payload becomes one opaque [N x i32] element, which puts the
// three appended values at element indices 1, 2 and 3.

// The appended values start immediately after a 4-byte payload and end the
// struct, so there is no padding of either kind.
// EXACTFIT: %PIX_AS2MS_Expanded_Type = type { [1 x i32], i32, i32, i32 }
// EXACTFIT: [[PAYLOAD:%[0-9]+]] = call %PIX_AS2MS_Expanded_Type* @dx.op.getMeshPayload.PIX_AS2MS_Expanded_Type(i32 170)
// EXACTFIT: getelementptr %PIX_AS2MS_Expanded_Type, %PIX_AS2MS_Expanded_Type* [[PAYLOAD]], i32 0, i32 1
// EXACTFIT: getelementptr %PIX_AS2MS_Expanded_Type, %PIX_AS2MS_Expanded_Type* [[PAYLOAD]], i32 0, i32 2
// EXACTFIT: getelementptr %PIX_AS2MS_Expanded_Type, %PIX_AS2MS_Expanded_Type* [[PAYLOAD]], i32 0, i32 3
// EXACTFIT: = !{{{![0-9]+}}, i32 4, i32 2, i32 2, i32 16}

// The amplification shader's struct was padded out to 32 bytes, so the
// synthesized type needs 16 bytes of explicit tail padding to reach the same
// total. Without it the mesh shader would declare 16 and the amplification
// shader 32.
// TAILPADDING: %PIX_AS2MS_Expanded_Type = type { [1 x i32], i32, i32, i32, [4 x i32] }
// TAILPADDING: = !{{{![0-9]+}}, i32 4, i32 2, i32 2, i32 32}

// An empty amplification shader payload expands to nothing but the three
// appended values, which is a legal zero-length leading array rather than a
// missing element - the appended values must stay at indices 1, 2 and 3.
// EMPTYPAYLOAD: %PIX_AS2MS_Expanded_Type = type { [0 x i32], i32, i32, i32 }
// EMPTYPAYLOAD: [[EMPTYPAYLOADPTR:%[0-9]+]] = call %PIX_AS2MS_Expanded_Type* @dx.op.getMeshPayload.PIX_AS2MS_Expanded_Type(i32 170)
// EMPTYPAYLOAD: getelementptr %PIX_AS2MS_Expanded_Type, %PIX_AS2MS_Expanded_Type* [[EMPTYPAYLOADPTR]], i32 0, i32 1
// EMPTYPAYLOAD: = !{{{![0-9]+}}, i32 4, i32 2, i32 2, i32 12}

// A 16-byte amplification shader payload whose last field ends at byte 16 - a
// uint4, say. The declared size alone would not have been enough to derive
// this: the same 16 bytes made of a uint64_t and a uint would have placed the
// appended values at byte 12 instead.
// MISMATCHEDLAYOUT: %PIX_AS2MS_Expanded_Type = type { [4 x i32], i32, i32, i32 }
// MISMATCHEDLAYOUT: = !{{{![0-9]+}}, i32 4, i32 2, i32 2, i32 28}

// The largest payload D3D allows is 16384 bytes, and the expansion is allowed
// to use every byte of it.
// MAXPAYLOAD: %PIX_AS2MS_Expanded_Type = type { [4092 x i32], i32, i32, i32, [1 x i32] }
// MAXPAYLOAD: = !{{{![0-9]+}}, i32 4, i32 2, i32 2, i32 16384}

struct PSInput
{
    float4 position : SV_POSITION;
};

struct MyPayload
{
    uint i;
};

[outputtopology("triangle")]
[numthreads(4, 1, 1)]
void MSMain(
    in payload MyPayload small,
    in uint tid : SV_GroupThreadID,
    out vertices PSInput verts[4],
    out indices uint3 triangles[2])
{
    SetMeshOutputCounts(4, 2);
    verts[tid].position = float4(0, 0, 0, 0);
    triangles[tid % 2] = uint3(0, tid + 1, tid + 2);
}
