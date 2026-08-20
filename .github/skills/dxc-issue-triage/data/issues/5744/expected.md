# Expected behavior (from issue text)

Issue: ddx_fine/ddy_fine (and by extension the other derivative DXIL ops:
Sample/SampleBias/SampleCmp/SampleCmpBias/CalculateLOD/DerivCoarseX/Y/DerivFineX/Y)
are marked `ReadNone`, same as ordinary side-effect-free unary ops. Because of
that, generic LLVM code motion (the "sink" pass mentioned in the report) is
free to move a derivative call that is only *used* inside one arm of an `if`
into that arm — even though the call itself was originally unconditional.
Derivatives read neighboring-thread (quad) values, so once the call only
executes on the lanes that take that branch, lanes outside the branch never
compute the value and the ones inside read partially-uninitialized quad data.

The issue's own repro is a runtime GPU test (`HelperLaneTestNoWave` /
`ExecutionTest::HelperLaneTest`, `hcttest exec-filter *HelperLaneTest`) and
needs a GPU adapter to observe the final numeric result. It is not necessary
to run on a GPU to observe the *compiler defect*, though: the defect is a
static code-motion decision, entirely visible in the generated DXIL/LLVM IR —
if the derivative call text appears after the conditional branch (i.e. moved
into a successor block) instead of before it (in the entry block, prior to
any branch), the compiler has performed the unsafe sink.

**"Reproduces" means:** compiling a pixel shader that computes a
`ddx_fine`/derivative value unconditionally and only *uses* the result inside
one arm of a real (non-select-folded) `if`, the disassembled DXIL shows the
`DerivFineX`/`DerivCoarseX`-class call placed *after* the `br i1` that begins
the conditional region (i.e. sunk into a successor block), rather than
computed once, unconditionally, before the branch.

**"Does not reproduce" means:** the derivative call stays in the entry block,
executed unconditionally before the branch, with only its *result* selected/
phi'd or stored conditionally afterward.

Repro quality: `agent-constructed`. The issue gives a real HLSL fragment
(`ReadAcrossX_DD`/`ReadAcrossY_DD`/`ReadAcrossDiagonal_DD`) and the exact
optimizer behavior it produces, but the full runtime harness
(`ShaderOpArith.xml`, `HelperLaneTestNoWave`, GPU adapter) is not something
this workflow can execute. The constructed repro below reduces the reported
shape (value read unconditionally, used only inside one `if` arm) to a
single derivative call, with a real (not select-converted) branch forced by
an accompanying UAV write so the branch is not folded away by
`SimplifyCFG`/if-conversion before the sink decision would matter.
