// RUN: %dxc -T lib_6_8 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-debug-instrumentation,parameter0=3,parameter1=1,parameter2=0 -hlsl-dxilemit | %FileCheck %s

// A coalescing node has no dispatch grid, so dx.op.threadId is not legal for it.
// ValidateDxilOperationCallInProfile in DxilValidation.cpp permits ThreadId and
// GroupId for a broadcasting launch only. The group-thread ID (SV_GroupThreadID)
// is legal, so the debugger discriminates invocations within a group by it.

// The requested thread must lie inside the declared thread group, or the pass
// discriminates nothing. The parameters above lie inside [NumThreads(4, 2, 1)].
// The pass report is emitted before the generated IR, so this must be checked
// before the first IR check below: CHECK-NOT only scans the window between the
// previous directive's match and the next directive's match, never anything
// outside that window. One CHECK-NOT before the positive report line only
// covers a stray None emitted before it; it says nothing about a stray None
// emitted after the positive report but still before the first IR check, since
// that text falls in the following window instead. Two CHECK-NOT directives,
// one on each side of the positive report line, are needed so the two windows
// together cover the entire report region and a stray erroneous
// NodeInvocationSelection:None cannot appear anywhere in it undetected.
// CHECK-NOT: NodeInvocationSelection:None

// CHECK: NodeInvocationSelection:GroupThreadId

// CHECK-NOT: NodeInvocationSelection:None

// CHECK: %ThreadIdX = call i32 @dx.op.threadIdInGroup.i32(i32 95, i32 0)
// CHECK: %ThreadIdY = call i32 @dx.op.threadIdInGroup.i32(i32 95, i32 1)
// CHECK: %ThreadIdZ = call i32 @dx.op.threadIdInGroup.i32(i32 95, i32 2)
// CHECK: %CompareToThreadIdX = icmp eq i32 %ThreadIdX, 3
// CHECK: %CompareToThreadIdY = icmp eq i32 %ThreadIdY, 1
// CHECK: %CompareToThreadIdZ = icmp eq i32 %ThreadIdZ, 0
// CHECK: %CompareAll = and i1 %CompareXAndY, %CompareToThreadIdZ
// CHECK: br i1 %CompareAll, label %PIXInterestingBlock, label %PIXNonInterestingBlock

RWStructuredBuffer<uint> Output : register(u0);

struct Record
{
  uint value;
};

[Shader("node")]
[NodeLaunch("coalescing")]
[NumThreads(4, 2, 1)]
void CoalescingNode(GroupNodeInputRecords<Record> input)
{
  Output[0] = input.Get(0).value;
}
