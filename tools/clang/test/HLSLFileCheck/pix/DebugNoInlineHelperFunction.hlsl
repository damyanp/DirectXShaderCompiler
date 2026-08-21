// RUN: %dxc -Emain -Tcs_6_0 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-debug-instrumentation,parameter0=1,parameter1=2,parameter2=3 | %FileCheck %s

// The annotation pass numbers the instructions of every function with a body and
// reports the resulting range to PIX, which is what lets PIX map a traced ordinal back
// to a source line. The debug instrumentation pass used to instrument only the entry
// point (plus, as a special case, a hull shader's patch constant function), so the
// ordinals belonging to a [noinline] helper were advertised but nothing ever wrote a
// trace record for them: PIX showed the user a call it could never step into.
//
// The two passes now agree on the same set of functions. Note that this does not
// disturb instruction numbering, which the annotation pass alone decides and which
// already covered these functions.

// The helper is numbered and reported...
// CHECK: InstructionRange: {{[0-9]+}} {{[0-9]+}} {{.*}}ScaleHelper

// ...and instrumented. Each instrumented function gets its own handle to the debug
// UAV and its own atomic allocation of a slot in it.
// CHECK: define internal fastcc float @{{.*}}ScaleHelper
// CHECK: %PIX_DebugUAV_Handle = call %dx.types.Handle @dx.op.createHandle(i32 57
// CHECK: call i32 @dx.op.atomicBinOp.i32(i32 78, %dx.types.Handle %PIX_DebugUAV_Handle

RWStructuredBuffer<float> Output : register(u0);

[noinline]
float ScaleHelper(float value)
{
  return value * 3.f;
}

[numthreads(1, 1, 1)]
void main(uint3 threadId : SV_DispatchThreadID)
{
  Output[threadId.x] = ScaleHelper(threadId.y);
}
