// RUN: %dxc -T lib_6_8 %s | %opt -S -dxil-annotate-with-virtual-regs -hlsl-dxil-debug-instrumentation,parameter0=1,parameter1=2,parameter2=3 | %FileCheck %s

// A thread launch node has neither a dispatch grid nor a thread group, so none of the
// thread-identity intrinsics are legal for it: ValidateDxilOperationCallInProfile in
// DxilValidation.cpp rejects ThreadId, GroupId, ThreadIdInGroup and
// FlattenedThreadIdInGroup for thread launch nodes. There is therefore nothing in the
// shader that distinguishes one invocation from another, and the pass deliberately
// keeps the select-everything criterion. This test pins that decision down so that a
// later change cannot quietly start emitting an intrinsic the validator will reject.

// CHECK: NodeInvocationSelection:None

// CHECK-NOT: @dx.op.threadId.i32
// CHECK-NOT: @dx.op.threadIdInGroup.i32
// CHECK-NOT: @dx.op.flattenedThreadIdInGroup.i32
// CHECK: br i1 true, label %PIXInterestingBlock, label %PIXNonInterestingBlock

RWStructuredBuffer<uint> Output : register(u0);

struct Record
{
  uint value;
};

[Shader("node")]
[NodeLaunch("thread")]
void ThreadLaunchNode(ThreadNodeInputRecord<Record> input)
{
  Output[0] = input.Get().value;
}
