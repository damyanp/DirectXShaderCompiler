// RUN: %dxc -T lib_6_6 -Od %s | %opt -S -hlsl-dxil-pix-shader-access-instrumentation,config=.256;512;1024. | %FileCheck %s

// A descriptor-heap access record carries the shader kind that made it, in the
// top four bits of the stored dword; PIX decodes it to a pipeline stage. The
// pass used to read that kind off the function containing the access, which
// only works for an entry point. A non-entry library helper has no
// DxilFunctionProps, so the lookup fell back to the module's kind - Library for
// any lib_6_x target - and PIX maps Library to PIX_PIPELINE_STAGE_NONE. Every
// bindless access made below an entry point, and every out-of-bounds warning
// about one, was therefore filed under no stage at all.
//
// HeapHelper is [noinline] so that it survives as its own function: without
// that DXC inlines it into RayGen even at -Od, the access lands in a function
// that does have props, and the encoding is correct for the wrong reason.
// Passing the descriptor index as a parameter is what keeps the helper from
// being folded away.
//
// The kind occupies bits 31:28 and the ResourceAccessStyle bits 27:24, except
// that an out-of-bounds record sets the instruction-ordinal indicator (bit 27)
// instead of a style. RayGeneration is 7 and UAVWrite is 3, so the in-bounds
// flags are 0x73000000 == 1929379840 and the out-of-bounds value is
// 0x78000000 == 2013265920. Under the module kind, Library (6), those would be
// 0x63000000 == 1660944384 and 0x68000000 == 1744830464.

// CHECK: define void {{.*}}HeapHelper
// CHECK-NOT: 1660944384
// CHECK: mul i32 {{.*}}, 1929379840
// CHECK-NOT: 1744830464
// CHECK: mul i32 {{.*}}, 2013265920

[noinline]
export void HeapHelper(uint descriptorIndex)
{
    RWByteAddressBuffer heapBuffer = ResourceDescriptorHeap[descriptorIndex];
    heapBuffer.Store(0, 1);
}

[shader("raygeneration")]
void RayGen()
{
    HeapHelper(1);
}
