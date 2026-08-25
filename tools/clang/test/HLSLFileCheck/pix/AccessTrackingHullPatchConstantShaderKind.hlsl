// RUN: %dxc -T lib_6_6 -Od %s | %opt -S -hlsl-dxil-pix-shader-access-instrumentation,config=.256;512;1024. | %FileCheck %s

// A hull shader's patch-constant function is associated by
// DxilFunctionProps (ShaderProps.HS.patchConstantFunc), not by a CallInst,
// so normal call-graph traversal never reaches it. PatchConstantFunction
// makes its own dynamic descriptor-heap access directly (reachable only
// through that metadata edge) and separately calls the [noinline]
// PatchHelper, which makes a distinct dynamic descriptor-heap access of
// its own (reachable only through PatchConstantFunction's own ordinary
// CallInst, once the metadata edge has already been followed). Without
// seeding the patch-constant function explicitly, both functions -- and
// both accesses -- fall through to the module's Library shader kind
// instead of Hull.

// The kind occupies bits 31:28. An out-of-bounds record sets the
// instruction-ordinal indicator (bit 27). Hull is 3 and UAVWrite is 3, so
// the in-bounds value is 0x33000000 == 855638016 and the out-of-bounds
// value is 0x38000000 == 939524096. Under the module kind, Library (6),
// those values would be 0x63000000 == 1660944384 and 0x68000000 ==
// 1744830464 (the same wrong constants AccessTrackingLibHelperShaderKind
// checks for the analogous RayGeneration case).

// Each function's own access is checked in isolation, scoped by
// CHECK-LABEL to that function's definition so neither function's
// records can satisfy the other's assertions. Within each function's
// window: neither Library value may appear anywhere before the
// in-bounds Hull value (this also rejects the out-of-bounds Hull value
// appearing before the in-bounds one, since the pass always emits the
// in-bounds mul first); the in-bounds value is required exactly once
// (immediately rejecting a duplicate before the out-of-bounds value is
// even reached); the out-of-bounds value is then required exactly once;
// and after it, every one of the four values (both Hull, both Library)
// is rejected again through to the function's own closing brace, so no
// duplicate or wrong-kind record can hide anywhere in the function body.
// The closing-brace check is the window's hard boundary: it cannot
// spill into the next function, unlike an unbounded trailing CHECK-NOT
// alone would.
//
// Function-name patterns anchor on "?<Name>@@", the exact boundary MSVC
// name mangling places immediately after an unqualified identifier (see
// the actual mangled names below, e.g. "?PatchHelper@@YAXI@Z"), so a
// same-prefixed but different function (e.g. a hypothetical
// "PatchHelperExtra", mangled "?PatchHelperExtra@@...") cannot satisfy
// the pattern. Numeric constants are token-terminated with a required
// trailing comma or end of line, so no value can be satisfied merely by
// being a numeric prefix of a longer, unrelated constant.

// CHECK-LABEL: define void {{.*}}?PatchHelper@@{{.*}}
// CHECK-NOT: 1660944384{{,|$}}
// CHECK-NOT: 1744830464{{,|$}}
// CHECK-NOT: 939524096{{,|$}}
// CHECK: mul i32 {{.*}}, 855638016{{,|$}}
// CHECK-NOT: 855638016{{,|$}}
// CHECK-NOT: 1660944384{{,|$}}
// CHECK-NOT: 1744830464{{,|$}}
// CHECK: mul i32 {{.*}}, 939524096{{,|$}}
// CHECK-NOT: 855638016{{,|$}}
// CHECK-NOT: 939524096{{,|$}}
// CHECK-NOT: 1660944384{{,|$}}
// CHECK-NOT: 1744830464{{,|$}}
// CHECK: }

// CHECK-LABEL: define void {{.*}}?PatchConstantFunction@@{{.*}}
// CHECK-NOT: 1660944384{{,|$}}
// CHECK-NOT: 1744830464{{,|$}}
// CHECK-NOT: 939524096{{,|$}}
// CHECK: mul i32 {{.*}}, 855638016{{,|$}}
// CHECK-NOT: 855638016{{,|$}}
// CHECK-NOT: 1660944384{{,|$}}
// CHECK-NOT: 1744830464{{,|$}}
// CHECK: mul i32 {{.*}}, 939524096{{,|$}}
// CHECK-NOT: 855638016{{,|$}}
// CHECK-NOT: 939524096{{,|$}}
// CHECK-NOT: 1660944384{{,|$}}
// CHECK-NOT: 1744830464{{,|$}}
// CHECK: }

struct PointOut
{
    float3 pos : POSITION;
};

struct ConstantOut
{
    float edges[3] : SV_TessFactor;
    float inside : SV_InsideTessFactor;
};

[noinline]
export void PatchHelper(uint descriptorIndex)
{
    RWByteAddressBuffer heapBuffer = ResourceDescriptorHeap[descriptorIndex];
    heapBuffer.Store(0, 1);
}

// primID is a valid patch-constant-function input (SV_PrimitiveID) that
// the compiler cannot constant-fold, so neither dynamic descriptor-heap
// access below can be eliminated or merged with the other: each reads a
// different, runtime-only index.
ConstantOut PatchConstantFunction(InputPatch<PointOut, 3> patch, uint primID : SV_PrimitiveID)
{
    // Direct access: reachable only through the HS -> patch-constant
    // metadata edge, never through any CallInst.
    RWByteAddressBuffer directBuffer = ResourceDescriptorHeap[primID];
    directBuffer.Store(4, 2);

    // Indirect access: reachable only through this function's own
    // ordinary CallInst to PatchHelper.
    PatchHelper(primID + 1);

    ConstantOut output;
    output.edges[0] = output.edges[1] = output.edges[2] = 1;
    output.inside = 1;
    return output;
}

[shader("hull")]
[domain("tri")]
[partitioning("integer")]
[outputtopology("triangle_cw")]
[outputcontrolpoints(3)]
[patchconstantfunc("PatchConstantFunction")]
PointOut main(InputPatch<PointOut, 3> patch, uint id : SV_OutputControlPointID)
{
    return patch[id];
}
