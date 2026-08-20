# #5491 — DXC does not eliminate wave intrinsic calls even when the result is unused

Written **before** running any compiler. Derived only from the issue text
(<https://github.com/microsoft/DirectXShaderCompiler/issues/5491>, filed 2023-08-03 by
@dmpots, 4 comments) and its Shader Playground link.

## What the reporter claims

```
// dxc /T ps_6_0 t.hlsl
[RootSignature("")]
void main(int a : A) {
  (void)WaveReadLaneFirst(a);
}
```

The call to `WaveReadLaneFirst` has its result discarded (`(void)` cast), so the reporter
expects ordinary dead-code elimination to remove the call along with any code that only feeds
it. Instead the final DXIL retains the call:

```llvm
define void @main() {
  %1 = call i32 @dx.op.loadInput.i32(i32 4, i32 0, i32 0, i8 0, i32 undef)
  %2 = call i32 @dx.op.waveReadLaneFirst.i32(i32 118, i32 %1)
  ret void
}
```

Reporter's DXC version: `1.6.2104.52 (e09a454eb)`. Also reproduced on Shader Playground
against dxc trunk at the time of filing (2023).

## Comment thread — read before judging this a simple DCE bug

- @llvm-beanz links PR #5559 ("Workaround for wave loop getting deleted") and related issues
  #5302, #5034, #5177, and labels this a **correctness** concern, not purely a missed
  optimisation: *"While in this case it is more an optimization issue, I'm not convinced that
  there isn't a correctness bug lurking here too."*
- @dmpots (the reporter) pushes back that #5302 is a different bug (the `dx.break` fix only
  applied to PS/CS/LIB targets), and @llvm-beanz agrees that was "breadcrumbs" from a quick
  skim, not a claim that they are the same defect.
- #5177 (`Dead code elimination not working for unused wave operations`, a `WaveActiveMax(0)`
  under `#if DEADCODE`) was closed by a maintainer as a **duplicate of this issue** on
  2023-10-03, with discussion continuing here — confirmed via the cross-reference timeline.
- PR #5559 is **closed, unmerged** (`mergedAt: null`). Its own description says the opposite
  direction of this report: it is a workaround so a wave op **is not** deleted from a loop
  where a "read only" assumption was wrong, and says explicitly "this might be the full fix,
  but requires more investigation." It is evidence that the project treats wave-op
  liveness/DCE as an open, partially-understood area, not evidence that this exact repro was
  fixed.

None of these establish that the specific single-call-with-discarded-result case in this issue
has been fixed; they establish that the surrounding DCE-vs-wave-op area is unsettled and that a
naive "wave ops are readnone" fix would be wrong in the loop case PR #5559 describes.

## What "this reproduces" means

Compiling the reporter's exact shader (`-T ps_6_0 -E main`, with `[RootSignature("")]` kept so
the shader is self-contained) and reading the emitted DXIL:

- **Reproduces** if the final DXIL still contains a `call ... @dx.op.waveReadLaneFirst.i32(...)`
  (or whichever `dx.op` the wave intrinsic lowers to) whose result is never used by any other
  instruction — i.e. the call has no users, exactly like the reporter's example.
- **Does not reproduce** if the wave-intrinsic call is absent from the final DXIL, i.e. DCE (or
  an equivalent pass) has removed it because its result feeds nothing.
- The presence of the antecedent `loadInput` computing the wave op's discarded argument is not
  itself part of the symptom — only the wave-intrinsic call's survival matters, since dead
  code that merely *feeds* an already-dead call could legitimately be removed by an unrelated
  optimisation while the call site the reporter is pointing at stays or goes independently. Both
  are recorded for completeness, but the verdict tracks the call.

## Compiler-source question worth checking independent of any single probe

`DxilOperations.cpp` assigns every DXIL opcode an `Attribute` (`ReadNone`, `ReadOnly`, or
`None`) that becomes the emitted LLVM function's attribute. A `ReadNone`/`ReadOnly` callee with
an unused result is exactly what standard LLVM DCE removes; `Attribute::None` is not, because
LLVM must conservatively assume an opaque external call may have side effects. If wave
intrinsics are declared `Attribute::None` in source, that is strong, independent evidence this
is *deliberate current behaviour* rather than a bug nobody looked at — DCE is doing exactly what
the declared attribute tells it to do. That would reframe "not eliminated" from a defect in the
DCE pass to a (possibly still open) design/labeling question about whether wave ops are safe to
mark otherwise, which is exactly the tension @llvm-beanz's comment raises.

## Repro quality

**complete.** The issue supplies the exact command line (`dxc /T ps_6_0 t.hlsl`) and a
self-contained 4-line shader. The only detail supplied by triage is the entry-point name
already implied by `void main(...)` and used verbatim (`-E main`).

## What would make this inconclusive

- If the shader fails to compile at all on current `main` (a front-end or root-signature
  change unrelated to this report).
- If DCE behaviour depends on optimisation level/flags not specified in the issue and the
  reporter's flags are ambiguous — record the default flags used and note that a different
  `-O` level was not part of the report.
