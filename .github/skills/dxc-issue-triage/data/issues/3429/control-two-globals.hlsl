// Second negative control for issue 3429, and a recorded negative result.
//
// Intent: construct from HLSL a GENUINELY ambiguous TGSM pointer -- one merged value whose
// incoming pointers come from two DIFFERENT groupshared globals -- which is the case the
// validation rule INSTR.FAILTORESLOVETGSMPOINTER exists to catch.
//
// Measured outcome: it does not happen. DXC compiles this cleanly at default -O3 and keeps
// two separate stores, one per branch, each GEPing its own global; no phi or select of
// 'float addrspace(3)*' is formed. See variant-control-two-globals-main-debug.txt.
//
// Worth recording rather than deleting. The repo's own negative test for this rule,
// tools/clang/test/LitDXILValidation/GroupShared/tgsm-chained-gep-ambiguous.ll, constructs
// the ambiguous phi and select in HAND-WRITTEN LLVM IR, not from HLSL. So the ambiguous case
// the rule is written for was not reachable from HLSL in this attempt, while the
// unambiguous case in repro.hlsl -- a phi both of whose inputs GEP the same global -- is
// produced by DXC's own optimizer from ordinary source. This does not prove that no HLSL can
// express the ambiguous case; it is one attempt that did not.
//
// Expected: no-match.

groupshared float alpha[6];
groupshared float beta[6];
groupshared uint counter;

[numthreads(8, 1, 1)]
void main(uint gi : SV_GroupIndex) {
  if (counter > 3)
    alpha[gi] = 1.0;
  else
    beta[gi] = 1.0;
}
