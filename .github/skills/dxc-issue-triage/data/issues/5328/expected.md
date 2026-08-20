# Expected symptom — issue #5328

Title: "Typo and potential null dereference in HLMatrixBitcastLowerPass.cpp"
Filed 2023-06-27 by adam-yang (reporter, a Microsoft contributor to this
repo). No HLSL repro or command line was provided; the reporter states
they filed an issue rather than a PR because they "didn't have a
reliable way to make a test case for it."

## Primary claim (issue body)

In `lib/HLSL/HLMatrixBitcastLowerPass.cpp`, `HLMatrixBitcastLowerPass::lowerMatrix`
(around line 229 at the time of filing, line 244 on current ground truth)
has an if/else-if chain over the users of a bitcast:

```cpp
else if (LoadInst *LI = dyn_cast<LoadInst>(U)) {
  ...
} else if (StoreInst *ST = dyn_cast<StoreInst>(U)) {
  IRBuilder<> Builder(LI);   // <-- should be Builder(ST)
  ...
}
```

Because `LI` and `ST` are declared in sibling arms of the same
if/else-if chain, `LI` is guaranteed to still be `nullptr` inside the
`StoreInst *ST` arm (the `dyn_cast<LoadInst>` in the earlier arm must
have failed, since `U` was matched as a `StoreInst` instead). Passing a
null `Instruction*` to `IRBuilder<>`'s single-argument constructor
dereferences it immediately (`IP->getContext()`), so **reaching this
branch at all is a guaranteed, deterministic null-pointer dereference**
— not merely a latent risk.

"Reproducing this issue" means: (a) the exact source text above is
still present unchanged in `HLMatrixBitcastLowerPass.cpp`, and, if a
runtime trigger can be constructed, (b) that trigger causes an access
violation (0xC0000005) or an unhandled-exception-shaped internal
failure (0xE0000001 / 0xE0000002) originating in
`HLMatrixBitcastLowerPass.cpp`'s `lowerMatrix`, not in any other pass.

`MatrixBitcastLowerPass` is registered only in `lib/HLSL/DxilLinker.cpp`
(`DxilLinkJob::RunPreparePass`), so it only runs for `dxc -T lib_6_x
-link ...` invocations, never for an ordinary single-module compile.
Any runtime trigger therefore requires a multi-module HLSL shader
library link with a matrix array crossing a function boundary in a way
the optimizer cannot fully inline/fold away before the pass runs.

## Comment (b) — a separate, unrelated crash

The 2026-04-27 comment by mandryskowski attaches a full HLSL repro
(WGSL-via-tint) and a captured crash. Its stack trace names
`HLMatrixLowerPass::replaceAllVariableUses` -> `CreateGEP` ->
`GetElementPtrInst::Create` -> `checkGEPType`, asserting in
`include/llvm/IR/Instructions.h`. That is **a different file
(`HLMatrixLowerPass.cpp`, not `HLMatrixBitcastLowerPass.cpp`), a
different function, and a different fault** from the one this issue
reports. It reproduces (see `manual-case-comment-crash-stack.txt`), but
it is evidence for a distinct defect, not for this issue's typo, and is
treated that way throughout this triage.

## Repro quality

`partial`. The reporter provided a complete, unambiguous source-level
diagnosis (exact file/line/code) but explicitly no test case. Several
agent-constructed multi-module `-link` attempts to trigger the runtime
crash directly were made (see `manual-case-link-attempt.py` /
`.txt`, `link-a.hlsl`, `link-b.hlsl`) and did not succeed within the
time available for this triage — `AlwaysInlinerPass` (which runs
immediately before `MatrixBitcastLowerPass` in the link pipeline)
inlines the cross-module call before the buggy pass ever sees a
fake-matrix-typed `StoreInst`. The primary verdict therefore rests on
static source analysis (exact code, blame, and `IRBuilder` constructor
semantics), not on an executed crash of the exact reported code path;
this is stated explicitly rather than papered over.
