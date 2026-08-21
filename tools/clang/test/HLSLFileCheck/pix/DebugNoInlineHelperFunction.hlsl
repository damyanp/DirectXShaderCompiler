// RUN: %dxc -Emain -Tcs_6_0 /Od /Zi %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-debug-instrumentation,parameter0=1,parameter1=2,parameter2=3 | %FileCheck %s
// RUN: %dxc -Emain -Tcs_6_0 /Od /Zi %s | %opt -S -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs -hlsl-dxil-debug-instrumentation,parameter0=1,parameter1=2,parameter2=3 | %FileCheck %s -check-prefix=LOCALS

// PIX identifies a shader invocation by the stream of records one thread writes into
// the debug UAV, and maps that stream to exactly one function. A [noinline] helper
// therefore cannot be instrumented as a function in its own right: its records would
// arrive under a second invocation identity for a thread that only ran once, and PIX
// would discard them as belonging to some other thread.
//
// The annotation pass instead inlines helpers into the entry point before anything is
// numbered, which is the same shape the front end produces for an ordinary helper, and
// which PIX already knows how to present: the helper's frame is recovered from the
// inlinedAt chain on each inlined instruction, and its locals stay attributed to it.

// One function, so one invocation identity.
// CHECK: InstructionRange: {{[0-9]+}} {{[0-9]+}} main cs
// CHECK-NOT: InstructionRange:

// CHECK: define void @main()
// CHECK-NOT: define {{.*}}ScaleHelper

// The helper's body is now part of the entry point, but debug info still names it, so
// PIX can rebuild the call stack the user expects to step through.
// CHECK: !DISubprogram(name: "ScaleHelper"
// CHECK: inlinedAt:

// The helper's local survives inlining still scoped to the helper, which is what puts
// it under the right frame in PIX's locals view rather than under main's.
// LOCALS: call void @llvm.dbg.declare({{.*}}; var:"scaled"
// LOCALS: ![[HELPER:[0-9]+]] = !DISubprogram(name: "ScaleHelper"
// LOCALS: !DILocalVariable({{.*}}name: "scaled", scope: ![[HELPER]],

RWStructuredBuffer<float> Output : register(u0);

[noinline]
float ScaleHelper(float value)
{
  float scaled = value * 3.f;
  return scaled;
}

[numthreads(1, 1, 1)]
void main(uint3 threadId : SV_DispatchThreadID)
{
  Output[threadId.x] = ScaleHelper(threadId.y);
}
