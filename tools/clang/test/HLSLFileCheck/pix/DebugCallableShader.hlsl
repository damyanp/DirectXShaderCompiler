// RUN: %dxc -T lib_6_3 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-debug-instrumentation,parameter0=1,parameter1=2,parameter2=3 | %FileCheck %s

// Callable shaders were absent from IsInstrumentableShaderKind, so a CallShader()
// target could not be debugged at all: the pass numbered its instructions and
// advertised them to PIX, but emitted no instrumentation, so PIX offered the user a
// callable it could never step into.
//
// A callable has no ray and no thread of its own, but dx.op.dispatchRaysIndex is legal
// in it (the shader mask for opcode 145 in DxilOperations.cpp includes Callable), and
// it reports the index of the ray generation invocation that is ultimately responsible
// for this call. That is the same identity PIX already uses to select a raygen, any-hit,
// closest-hit or miss invocation, so a callable is selected on the raygen index too.

// The callable is the only shader in the module, so a Block# line at all means it
// was instrumented. Today there is none: the pass emits only InstructionRange for it.
// CHECK: Block#

// CHECK: %RayX = call i32 @dx.op.dispatchRaysIndex.i32(i32 145, i8 0)
// CHECK: %RayY = call i32 @dx.op.dispatchRaysIndex.i32(i32 145, i8 1)
// CHECK: %RayZ = call i32 @dx.op.dispatchRaysIndex.i32(i32 145, i8 2)
// CHECK: %CompareToThreadIdX = icmp eq i32 %RayX, 1
// CHECK: %CompareToThreadIdY = icmp eq i32 %RayY, 2
// CHECK: %CompareToThreadIdZ = icmp eq i32 %RayZ, 3
// CHECK: %CompareAll = and i1 %CompareXAndY, %CompareToThreadIdZ
// CHECK: br i1 %CompareAll, label %PIXInterestingBlock, label %PIXNonInterestingBlock

RWStructuredBuffer<float> Output : register(u0);

struct CallableParameters
{
  float value;
};

[shader("callable")]
void MyCallable(inout CallableParameters parameters)
{
  parameters.value = parameters.value * 2.f;
  Output[0] = parameters.value;
}
