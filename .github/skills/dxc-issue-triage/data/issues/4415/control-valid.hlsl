// #4415 NEGATIVE CONTROL for match.json clause 1.
//
// The issue's repro with exactly one thing changed: the ConstantBuffer is
// initialized from a literal heap index instead of from its own uninitialized
// member. Everything else -- profile, entry point, types, the arguments in
// cmd.txt -- is identical, so this differs from repro.hlsl in one way only.
//
// Expected: compiles clean, and every dx.op.annotateHandle takes a real handle
// produced by dx.op.createHandleFromHeap, so match.json's clause 1
// ("annotateHandle(i32 216, %dx.types.Handle zeroinitializer") cannot fire.
// That is what proves clause 1 discriminates on the handle operand rather than
// matching any successful vs_6_6 compile.

struct MyCB {
  uint u;
};
static ConstantBuffer<MyCB> CBV = ResourceDescriptorHeap[0];

uint main() : OUT {
  return CBV.u;
}
