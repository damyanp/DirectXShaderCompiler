# #5448 -- Organize usage of GetResourceFromHandle and GetResourceFromVal calls in validation

## What was tested

This is an internal validator code-organization / tech-debt request, filed by
the issue's own reporter six minutes after their PR
[#5399](https://github.com/microsoft/DirectXShaderCompiler/pull/5399) merged
(confirmed: `gh pr view 5399` reports `mergedAt: 2023-07-22T01:06:04Z`;
`issue.json`'s `createdAt` is `2023-07-22T01:12:41Z`). PR #5399 added the
up-front handle-argument validation pass
(`ValidateHandleArgsForInstruction`/`ValidateHandleArgs`,
`DxilValidation.cpp:559-600`); this issue is the reporter's own follow-up
noting that the rest of the file's use of `GetResourceFromHandle` versus
`GetResourceFromVal` was left disorganized by that change and should be
cleaned up. There is no dxc.exe command line that tests a request to
reorganize source code, so the evidence here is direct source inspection at
ground truth `main-debug`, whose tree is confirmed identical to public
upstream `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` outside this skill
directory (`version-verification.txt`, with a positive control proving the
diff query can detect a real difference).

Full citations, with line numbers and quoted code, are in
`source-evidence.txt`. Summary:

1. **Both names still exist, unrenamed.** `GetResourceFromHandle`
   (`DxilValidation.cpp:167-189`) still both looks up resource properties via
   `GetResourceFromVal` *and* emits `InstrHandleNotFromCreateHandle` /
   `InstrReorderCoherentRequiresSM69` as a side effect. No
   `ValidateResourceHandle` function exists anywhere in the tree (confirmed
   by both a grep and `git log --all -i --grep=ValidateResourceHandle`,
   0 hits).
2. **The up-front pass PR #5399 added does run once per handle argument**
   (`ValidateHandleArgsForInstruction`, called from `ValidateHandleArgs`,
   called unconditionally at `DxilValidation.cpp:2283` for every resource
   dxil op) -- but nothing stops the *next* line in the same dispatch
   function, `ValidateResourceDxilOp` at line 2321, from also reaching
   `GetResourceFromHandle` for the identical operand through
   `GetResourceKindAndCompTy` (`GetDimensions` and others),
   `GetSamplerKind`, or `GetCBufSize` -- the exact three functions the issue
   names. There is no early return between the two calls. An invalid handle
   reaching, e.g., `GetDimensions` therefore still has
   `InstrHandleNotFromCreateHandle` emitted twice for the same instruction:
   once from the up-front pass, once from the op-specific accessor. This is
   the precise architecture the issue describes as a mess, and it is still
   the current architecture, not a historical one PR #5399 already fixed.
3. **The inconsistency itself, not just the duplicate emission, is
   confirmed.** `ValidateASHandle` (`DxilValidation.cpp:1572-1579`, used for
   `TraceRay`'s acceleration-structure handle) already does exactly what the
   issue asks for everywhere: call the silent `GetResourceFromVal`, check
   validity itself, and emit one specific diagnostic. Two more call sites
   (`DxilValidation.cpp:2383`, `:2655`) also already call
   `GetResourceFromVal` directly. So both styles coexist side by side today,
   which is exactly the "currently a mess" the issue's title names.
4. **`DxilResourceProperties::isValid()` exists
   (`include/dxc/DXIL/DxilResourceProperties.h:79`,
   `lib/DXIL/DxilResourceProperties.cpp:34-36`) and is never called from
   `DxilValidation.cpp`** -- every call site instead repeats
   `RP.getResourceClass() == DXIL::ResourceClass::Invalid` (or the
   resource-kind equivalent) by hand, exactly contrary to the issue's ask
   that callers "should be using GetResourceFromVal() and IsValid()".
5. **No commit has ever implemented any part of this**: `git log --all
   --oneline -i --grep="GetResourceFromHandle"`,
   `--grep="ValidateResourceHandle"`, `--grep="5448"`, and
   `git log --all --oneline -S"ValidateResourceHandle" --
   lib/DxilValidation` all return zero commits.
6. **No comments, no cross-references.** `fetch` recorded `comments: 0`;
   `gh api .../issues/5448/timeline` lists only `labeled`,
   `added_to_project_v2`, `project_v2_item_status_changed`, `unlabeled`,
   `milestoned` events -- no `cross-referenced` event and no maintainer
   discussion exists to check the text against.

**Why no `cmd.txt`/`match.json`/Compiler Explorer link exist for this
issue:** the one concrete, externally-observable consequence named in the
issue -- a duplicate diagnostic for the same invalid handle -- requires a
resource-handle `Value` that is a `CallInst` but was never entered into
`ValidationContext::ResPropMap` (i.e., not a recognised
`CreateHandle`/`CreateHandleForLib`/`AnnotateHandle` result) reaching a
resource dxil op. Ordinary HLSL cannot construct that: the only source-level
way to make a handle come from something other than one static
`CreateHandle` call is to dynamically select between two different resource
objects, and DXC's own legalizer rejects that before DXIL validation ever
runs. This was confirmed directly, not assumed: `control-dynamic-handle-select.hlsl`
selects between two `Texture2D` locals by index and is rejected by
`main-debug` with `local resource not guaranteed to map to unique global
resource` at exit `0x80004005` (E_FAIL, an ordinary diagnosed error, not an
internal failure) -- captured with `triage.py run` as
`variant-control-main-debug.txt`. Reaching the validator's own
bad-handle branch needs directly hand-authored malformed DXIL run through the
standalone validator (`dxv`) rather than dxc.exe's compile-then-validate
pipeline; `dxv.exe` is not built in this environment (`build/Debug/bin`
contains only `clang-tblgen`, `dxc`, `FileCheck`, `llvm-tblgen`), and building
it is a new build target -- explicitly out of scope, since this task
disallows rebuilding anything shared. Per SKILL.md's guidance for
capability/organization questions, `match.json` and `cmd.txt` are therefore
deliberately absent rather than manufactured to look complete, and
`godbolt --skip` was recorded with the same reasoning: Compiler Explorer
would only compile well-formed source through the identical front end that
already blocks this path, adding nothing beyond the control above.

`bisect` is not applicable for the same reason as `godbolt`: there is no
release-to-release history of a source-organization decision to locate --
this is a request about the current codebase's structure, not a regression.

## Assessment

The issue is exactly what it says, and it remains completely unaddressed:
`GetResourceFromHandle` and `GetResourceFromVal` still coexist with the same
names and the same split responsibilities described in 2023, the three named
accessor functions still route through the error-emitting function rather
than the silent one, `isValid()` is still unused by the validator, and no
`ValidateResourceHandle`-style rename has happened. The codebase already
demonstrates the target pattern works (`ValidateASHandle`'s
`GetResourceFromVal` + manual validity check), which is evidence the
requested refactor is a mechanical, low-risk cleanup rather than a design
question -- consistent with this being filed as `tech-debt` immediately
after a related PR, not as a bug report.

No part of the issue's text is stale: it describes the current architecture
precisely, and nothing about it (title, body, or the referenced PR
discussion) has become inaccurate.

Sampling note: this is a single tech-debt/enhancement issue with no shader
repro and no release history; its verdict process (source inspection only,
no bisection, no Compiler Explorer link) does not generalize to
crash/regression issues in the same batch.
