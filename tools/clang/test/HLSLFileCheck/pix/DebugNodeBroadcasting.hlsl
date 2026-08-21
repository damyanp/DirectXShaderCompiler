// RUN: %dxc -T lib_6_8 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-debug-instrumentation,parameter0=10,parameter1=20,parameter2=30 | %FileCheck %s

// A broadcasting node is dispatched over a grid, so SV_DispatchThreadID names an
// invocation in exactly the way it does for a compute shader and the debugger can
// select the one the user asked for. Before this was implemented the pass emitted a
// constant-true criterion for every node shader, so every invocation believed it was
// the selected one and the debugger showed whichever one won the race to the UAV.

// CHECK: NodeInvocationSelection:DispatchThreadId

// CHECK: %ThreadIdX = call i32 @dx.op.threadId.i32(i32 93, i32 0)
// CHECK: %ThreadIdY = call i32 @dx.op.threadId.i32(i32 93, i32 1)
// CHECK: %ThreadIdZ = call i32 @dx.op.threadId.i32(i32 93, i32 2)
// CHECK: %CompareToThreadIdX = icmp eq i32 %ThreadIdX, 10
// CHECK: %CompareToThreadIdY = icmp eq i32 %ThreadIdY, 20
// CHECK: %CompareToThreadIdZ = icmp eq i32 %ThreadIdZ, 30
// CHECK: %CompareXAndY = and i1 %CompareToThreadIdX, %CompareToThreadIdY
// CHECK: %CompareAll = and i1 %CompareXAndY, %CompareToThreadIdZ
// CHECK: br i1 %CompareAll, label %PIXInterestingBlock, label %PIXNonInterestingBlock

RWStructuredBuffer<uint> Output : register(u0);

struct Record
{
  uint value;
};

[Shader("node")]
[NodeLaunch("broadcasting")]
[NodeDispatchGrid(2, 1, 1)]
[NumThreads(4, 2, 1)]
void BroadcastingNode(DispatchNodeInputRecord<Record> input)
{
  Output[0] = input.Get().value;
}
