// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=16,expanded-payload-offset=6 | %FileCheck %s
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=18,expanded-payload-offset=4 | %FileCheck %s
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=12,expanded-payload-offset=4 | %FileCheck %s
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=16388,expanded-payload-offset=4 | %FileCheck %s
// RUN: %dxc -EMSMain -Tms_6_6 %s | %opt -S -hlsl-dxil-pix-meshshader-output-instrumentation,expand-payload=1,UAVSize=8192,expanded-payload-size=16,expanded-payload-offset=4294967292 | %FileCheck %s

// The size and offset the pass synthesizes an unread payload's type from come
// from PIX over the pass-options string, so the pass validates them rather than
// trusting them. Each RUN line above is one way for them to be unusable:
//
//   1. an offset that is not dword-aligned, which no payload layout produces;
//   2. a total size that is not dword-aligned, same;
//   3. a total too small to hold the three appended dwords at that offset;
//   4. a total larger than the 16384 bytes D3D permits;
//   5. an offset so large that adding the appended dwords' size to it wraps
//      around 32 bits. That one used to pass every other check and produce a
//      %PIX_AS2MS_Expanded_Type whose leading padding array was a billion
//      dwords - four gigabytes - while the declared payload size stayed at 16.
//
// In every case the expansion is abandoned rather than guessed at. The wrong
// payload layout is worse than none: it makes the mesh shader read the
// disambiguation values out of arbitrary bytes, and a wrong declared size makes
// PSO creation fail outright.
//
// The CHECK-NOT directives below are interleaved between every pair of positive
// CHECKs rather than grouped at the top, because a CHECK-NOT only applies to the
// span between its neighbouring matches. Grouped at the top they would leave the
// body of the function - where a getMeshPayload call would appear - unscanned.

// Nothing was expanded, so there is no synthesized payload type and no payload
// access. This span also covers the module's type definitions, where a
// %PIX_AS2MS_Expanded_Type declaration would appear.
// CHECK-NOT: %PIX_AS2MS_Expanded_Type
// CHECK-NOT: getMeshPayload

// Instrumentation still happens; only the payload expansion is skipped. With no
// payload to read the launching amplification-shader thread from, the
// disambiguation value falls back to flattening the group id with the dispatch
// arguments, which default to 1. That fallback is the observable consequence of
// the rejection, so it is what proves the pass took the intended path rather
// than merely doing nothing.
//
// These come first in the emitted function, before the debug UAV handle.
// CHECK: %GroupIdX = call i32 @dx.op.groupId.i32(i32 94, i32 0)
// CHECK: %GroupIdY = call i32 @dx.op.groupId.i32(i32 94, i32 1)
// CHECK: %GroupIdZ = call i32 @dx.op.groupId.i32(i32 94, i32 2)
// CHECK: mul i32 %GroupIdY, 1
// CHECK: add i32 %GroupIdZ,
// CHECK: mul i32 %GroupIdX, 1

// CHECK-NOT: %PIX_AS2MS_Expanded_Type
// CHECK-NOT: getMeshPayload

// CHECK: %PIX_DebugUAV_Handle = call %dx.types.Handle @dx.op.createHandleFromBinding

// CHECK-NOT: %PIX_AS2MS_Expanded_Type
// CHECK-NOT: getMeshPayload

// CHECK: call void @dx.op.bufferStore.i32

// CHECK-NOT: %PIX_AS2MS_Expanded_Type
// CHECK-NOT: getMeshPayload

// CHECK: call void @dx.op.storeVertexOutput.f32

// This trailing pair covers the rest of the module, including the declare block
// where a @dx.op.getMeshPayload declaration would survive.
// CHECK-NOT: %PIX_AS2MS_Expanded_Type
// CHECK-NOT: getMeshPayload

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
