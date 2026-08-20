# Issue 5434 — notes

**Title:** [Validation] Add validation for Annotate*Handle intrinsics
**Filed:** 2023-07-18, by bob80905 (Joshua Batista, a DXC maintainer). No comments.
**Labels at fetch:** `enhancement`, `tech-debt`, `validation`.

## What the issue asks for

Two related asks, both about `DxilValidation.cpp`:

1. Validate `Annotate*Handle` intrinsics "deeper than just validating that the handle
   arguments are valid."
2. Check that a handle actually originated from a valid source (a `Create*Handle` call,
   an external constant, etc.), not just that it looks structurally like a handle.

## Source reading: the gap is explicit and named

`lib/DxilValidation/DxilValidation.cpp`, `ValidateHandleArgs` (called for every DXIL
call instruction that takes a handle-typed operand):

```cpp
switch (Opcode) {
  // TODO: add case DXIL::OpCode::IndexNodeRecordHandle:

case DXIL::OpCode::AnnotateHandle:
case DXIL::OpCode::AnnotateNodeHandle:
case DXIL::OpCode::AnnotateNodeRecordHandle:
case DXIL::OpCode::CreateHandleForLib:
  // TODO: add custom validation for these intrinsics
  break;

default:
  ValidateHandleArgsForInstruction(CI, Opcode, ValCtx);
  break;
}
```

`ValidateHandleArgsForInstruction` is exactly the check the issue is asking for — at
minimum it rejects an `undef`/`zeroinitializer` handle operand
(`InstrNoReadingUninitialized`), and for a resource handle also validates it through
`GetResourceFromHandle`. Every DXIL opcode that consumes a handle goes through it
**except** the four listed above, which hit the `TODO` and get no check at all. This is
a direct, source-level confirmation that the requested validation does not exist for
`AnnotateHandle` / `AnnotateNodeHandle` / `AnnotateNodeRecordHandle` (the three the issue
title names — `CreateHandleForLib`'s operand is a resource-struct pointer, not one of the
three handle types this function checks, so it isn't part of this probe).

## History of the gap

`git log --all -S "TODO: add custom validation for these intrinsics"` finds this string
introduced in commit `9468120e6` ("[Validation] Prevent instructions that accept handle
arguments from accepting malformed handle arguments (#5399)", 2023-07-21 — three days
*after* #5434 was filed) and reintroduced verbatim by `8a8b29f96` ("[spirv] AMD work
graphs extension (#7353)", 2025-06-03), which is a large restructure of the validation
file, not a change to this switch. #5399's own description says it "intends to at least
implement the first work item" of a linked issue (#5356, closed, filed 2023-06-28), whose
priority list has null/undef handle rejection as item 1 — implemented for every opcode
*except* these four, which the PR explicitly deferred with the TODO. #5434 is asking for
exactly the deferred piece. Nothing found in the repository has since closed that gap;
`git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` (this batch's triage
branch vs. ground truth) touches nothing outside `.github/skills/dxc-issue-triage`, so
ground truth here is exactly what a clean checkout of the cited commit contains.

Cross-reference timeline (`gh api .../issues/5434/timeline`) has exactly one entry: a
2023-11-08 mention from #5982 ("Shader Model 6.8"), a tracking issue that lists this as
related work, not a fix. No other repository activity references #5434.

## Measurement: hand-constructed DXIL through the validator

No repro was provided, and none is reconstructable from HLSL: dxc's front end always
CodeGens a matching `Create*Handle` → `Annotate*Handle` pair, so the only way to present
the validator with a handle that didn't come from a legitimate create call is to
hand-write DXIL that violates the invariant directly (as the existing test suite already
does for the *checked* opcodes — see
`tools/clang/test/DXILValidation/validate_undef_arg.ll`, which documents that same
technique for every op the gap does not cover, and
`tools/clang/test/LitDXILValidation/createHandleFromBinding_non_constant_bind.ll`, whose
`AnnotateHandle`/`ResourceProperties` shape this probe reuses).

**Harness note.** This batch's shared ground-truth build only produced `dxc.exe` (`dxv.exe`
was not built, and building it was out of scope — no rebuild of the shared build tree for
this issue). `dxv.exe` loads its validator dynamically: `tools/clang/tools/dxv/dxv.cpp`
calls `DxcCreateInstance` against whichever `dxcompiler.dll` sits next to it. So a scratch
directory holds a **released** `dxv.exe`/`dxil.dll` (from the already-downloaded
v1.8.2502 archive) with **main-debug's own `dxcompiler.dll`** copied in beside them —
an unmodified host binary exercising ground-truth's validator, the same "component
cross-probe" idea `SKILL.md` documents for `dxopt -external`. Proved, not assumed
(`manual-case-dll-swap-proof.txt`): with `dxcompiler.dll` renamed out of the scratch
directory, `dxv.exe` fails immediately with `0x8007007E` (`ERROR_MOD_NOT_FOUND`) instead
of validating — so whichever `dxcompiler.dll` is present is the one actually driving the
result, not a cached or system-wide copy. `validate-with-dxv.py` in this directory
generates every capture and echoes the exact command run
(`subprocess.list2cmdline`); the harness binaries themselves are cache artifacts,
not committed (see the file's docstring for the two-copy-command setup).

Three files, all lib_6_8 / cs_6_8 DXIL, checked to pass every prior validation stage
(module structure, shader-model gating, flags) so the only variable is the handle
argument of the opcode under test:

- `variant-annotatehandle-zero.ll` — `AnnotateHandle` (opcode 216) called with a
  `zeroinitializer` and, separately, an `undef` `%dx.types.Handle`, neither derived from
  any `Create*Handle` call.
- `variant-annotatenodehandles-zero.ll` — the same for `AnnotateNodeHandle` (249) and
  `AnnotateNodeRecordHandle` (251), reusing `validate_undef_arg.ll`'s exact node-entry
  metadata skeleton so only the tested opcode's operand differs from a file already known
  to validate structurally.
- `control-bufferupdatecounter-zero.ll` — the **same** zero/undef `%dx.types.Handle`
  value fed instead to `BufferUpdateCounter` (70), an ordinary handle-consuming opcode
  that does go through `ValidateHandleArgsForInstruction`.

### Result (main-debug, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`)

| file | opcode(s) under test | result |
| --- | --- | --- |
| `variant-annotatehandle-zero.ll` | AnnotateHandle | **`Validation succeeded.`** — no diagnostic |
| `variant-annotatenodehandles-zero.ll` | AnnotateNodeHandle, AnnotateNodeRecordHandle | **`Validation succeeded.`** — no diagnostic |
| `control-bufferupdatecounter-zero.ll` | BufferUpdateCounter (control) | `error: Instructions should not read uninitialized value.` (×2, one per zero/undef call), plus resource-kind errors that only fire once the handle is accepted as a real one |

Full captures: `manual-case-main-debug.txt`. The control is the anti-vacuity check the
absence findings need: the exact same malformed handle value **is** rejected the moment
it is consumed by an opcode that isn't on the TODO list, so the clean result for the three
`Annotate*` files is about the opcode, not about zero/undef handles being accepted
everywhere in this DXIL module.

### Corroboration against a released validator

The same three files were also run against the v1.8.2502 (2025-02) release's own
`dxcompiler.dll` (`manual-case-release-1.8.2502-corroboration.txt`): identical outcome —
`AnnotateHandle`/`AnnotateNodeHandle`/`AnnotateNodeRecordHandle` validate clean,
`BufferUpdateCounter` is rejected. This is not a bisection (there is nothing to bisect —
the TODO has been present, unmoved, since before the issue was filed, and this is a
feature that was never implemented rather than one that regressed), but it does confirm
the gap is not specific to this Debug build: the same released validator that ships today
has never enforced this either. As a same-harness sanity check, both the ground-truth and
the released `dxcompiler.dll` also agree on all 8 diagnostics in
`tools/clang/test/DXILValidation/validate_undef_arg.ll` (the existing positive control for
the *checked* opcodes; see `manual-case-main-debug.txt`'s run against that file, and the AB
comparison recorded when the harness was first validated) — the general check has not
drifted between the two builds either, which is what makes the released-build
corroboration meaningful rather than coincidental.

## Verdict

`repros` — the exact validation gap the issue describes is present at ground truth. Repro
quality is `agent-constructed` (hand-built DXIL; no reporter-supplied source). History is
`always-repro'd`: the four-opcode carve-out has existed, unchanged, since the commit that
added the general handle check three days after this issue was filed, and is unchanged in
the current released validator as well as in `main-debug`. This is a confirmed tech-debt /
enhancement gap, not a regression, so there is no "fixed-in"/"regressed-in" release to
report. Confidence: high for the absence of the specific check (directly observed and
source-confirmed); the issue's second ask ("or came from an external constant, etc.") is
broader than what was measured here and is left as future scope, not claimed as tested.

Not sent to Compiler Explorer: the defect only shows up when the validator is handed DXIL
that a legitimate compile can never produce, and CE's `dxc` panes compile HLSL source, not
raw `.ll` fed to the standalone validator — see `godbolt --skip` reason recorded on the
issue row.
