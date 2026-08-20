# Notes: #6003 [Valgrind] Conditional branches on uninitialized SourceLocation::ID

## Ground truth

Compiler `main-debug`, registered `git_commit = 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
("[HLSL] Add LinAlg descriptor I/O offset, stride and layout coverage (#8762)", 2026-08-12).

`dxc --version` on the currently-built `build/Debug/bin/dxc.exe` self-reports commit
`7665270b9` ("Merge remote-tracking branch 'origin/main' into triage", 2026-08-18), 27 commits
ahead of the registered `89e2f98e...` -- the working tree was rebuilt by other, parallel
triage activity in the shared build directory after `main-debug` was registered. Per the
tree-not-SHA rule: `git diff --name-only 89e2f98e...7665270b9` returns **179 files, all of
them under `.github/skills/`** (other batches' triage artifacts) and **zero files outside that
tree**. No compiler source differs between the registered commit and the binary actually on
disk, so the binary is valid ground truth for `89e2f98e...` despite the mismatched
self-reported SHA. This triage does not rebuild anything (out of scope for this task), so the
binary was used as-is.

## What the issue reports

Two independent Valgrind memcheck findings from a Linux debug build, both triggered by:

```
valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes dxc -T lib_6_4 -spirv \
  -fspv-target-env=vulkan1.2 -enable-16bit-types -HV 2021 -O0 -Zi shader.hlsl -Fo shader.spv
```
compiling a `raygeneration` shader that calls `Texture2D::SampleLevel`.

### Ask 1 -- uninitialised `SourceLocation::ID` via `TypeLoc::getBeginLoc()` (still open)

Stack: `clang::TypeLoc::getBeginLoc() (TypeLoc.cpp:195)` <- `TreeTransform<TemplateInstantiator>
::TransformType` <- `Sema::SubstType` <- `TemplateDeclInstantiator::VisitFieldDecl` <-
`Sema::InstantiateClass` <- `Sema::InstantiateClassTemplateSpecialization` <-
`Sema::RequireCompleteType`, ultimately reached while instantiating a field of the synthetic
HLSL vector class template built by `HLSLExternalSource::NewSimpleAggregateType` /
`GetOrCreateVectorSpecialization` / `LookupVectorType` in `SemaHLSL.cpp`. The uninitialised
value traces (via `--track-origins=yes`) to a heap slab from `ASTContext::Allocate`, i.e. an
allocator-fresh block that was never fully initialised before `TypeLoc::getBeginLoc()` branched
on part of it.

Comment from `sudonatalie` (2023-11-21): this warning is also seen compiling to plain DXIL, so
it is not SPIR-V-specific -- it is upstream Sema/AST instantiation code, essentially unmodified
Clang internals plus one HLSL-specific caller (`NewSimpleAggregateType`) that synthesizes a
vector type's `FieldDecl`s.

**Searched for a fix and found none:**
- `git log --all -S "TypeLoc::getBeginLoc" -- tools/clang/lib/AST/TypeLoc.cpp` returns only the
  first commit and two unrelated later touches (WSL test-breakage fix, AMD workgraphs) -- the
  function itself is unchanged since import.
- `git log --all -i --grep="valgrind"` and `--grep="uninitiali[sz]ed" -- tools/clang/lib/Sema
  tools/clang/lib/AST include/clang/AST` return no commit addressing this call chain. The one
  closest hit, `b34264708` ("Enable clang warnings for uninitialized variables/structs
  (#2424)"), was reverted five commits later by `d570a7da9`.
- No commit touches `NewSimpleAggregateType`, `GetOrCreateVectorSpecialization` or
  `LookupVectorType` to add explicit `TypeSourceInfo`/`TypeLoc` initialisation.

**What this environment can and cannot show:** Valgrind/memcheck requires a Linux build; this
session is Windows-only, and rebuilding dxc (Linux or otherwise) is explicitly out of scope for
this triage. Running the exact repro (`out-main-debug.txt`) and the DXIL-targeted variant
(`variant-dxil-main-debug.txt`) on the Windows ground-truth build both compile cleanly, exit 0,
with only an unrelated `-Wunused-value` warning -- consistent with the report (Valgrind flags
this as "still reachable"/a conditional-jump warning, not a crash, so a clean exit here neither
confirms nor refutes it). **Verdict for this ask: `not-compiler-verifiable`** -- the instrument
needed to observe the symptom (Valgrind/MSan on Linux) is unavailable, and no source change
addressing it was found, so the honest read is "unconfirmed, likely still present" rather than
"fixed".

### Ask 2 -- OOB/uninitialised-index read at `SemaHLSL.cpp:6465` (already fixed before filing)

The issue body itself states: *"Turns out this has been already fixed on the main branch. Would
be great if we see this change in the next release."* -- checked by the reporter against a
main build at hash `ceff9b804` as of filing (2023-11-10), reproducing only on the
`v1.7.2308`-sourced build they used for the write-up.

Confirmed independently by reading source:
- `git show 108c34654 -- tools/clang/lib/Sema/SemaHLSL.cpp` ("Fix asan stack use after return
  (#5628)", 2023-09-14, ~2 months before the issue was filed) is exactly this fix. Its commit
  message: *"In cases where arg 0's template id set to one of INTRIN_TEMPLATE_FROM_TYPE,
  INTRIN_TEMPLATE_VARARGS, or INTRIN_TEMPLATE_FROM_FUNCTION), this code would erroneously index
  beyond Template's size. ASAN helped to catch this error, reporting it as a use-after-return."*
  The diff changes exactly the reported line,
  `if (Template[pIntrinsic->pArgs[0].uTemplateId] == AR_TOBJ_OBJECT)`, to guard it with
  `if (pIntrinsic->pArgs[0].uTemplateId < MaxIntrinsicArgs) { ... }`.
- Reading `tools/clang/lib/Sema/SemaHLSL.cpp` **at the ground-truth commit
  `89e2f98e...`** directly (not by ancestry, per the tree-not-SHA guidance) shows the same call
  site (now at a different line number after later edits, guarded by a `qwUsage` / special
  template-id exclusion check) still carries the equivalent bounds check immediately before the
  array read: `CAB(pIntrinsic->pArgs[0].uTemplateId < MaxIntrinsicArgs, 0);` followed by
  `if (AR_TOBJ_UNKNOWN == Template[pIntrinsic->pArgs[0].uTemplateId])`. The protection is
  present and, if anything, more defensive than the original 2023-09-14 fix.
  (Note: `git merge-base` between `108c34654` and the ground-truth commit returns nothing in
  this local clone -- the repo carries many divergent/rewritten branches -- so ancestry could
  not be established mechanically; the direct source read at the exact ground-truth commit is
  used instead and is the stronger check per this skill's own guidance.)

**Verdict for this ask: `does-not-repro` / already fixed, and was already fixed before the
issue was even opened.**

## Overall

Because the issue bundles a still-open, unverifiable-here finding with a separately-resolved
one, the overall status is recorded as `not-compiler-verifiable` (the open ask is the one that
needs a decision), with the resolved ask called out explicitly in the summary and comment so a
maintainer does not have to re-derive it.

## Labels

Current: `bug`, `sanitizer`. Both are accurate (`bug`: "Bug, regression, crash"; `sanitizer`:
"fault detected by sanitizer run" -- this is exactly a sanitizer/memcheck-detected fault). No
removal is supported by the evidence. No addition proposed: `check-in-clang` would require
evidence that the new Clang-based front end shares the same synthetic vector-template
instantiation path, which was not investigated (out of scope: this is a Sema-only,
source-reading question about a component this triage did not need to touch to answer the
issue as filed).

## Artifacts

- `expected.md` -- symptom definition, written before any run.
- `repro.hlsl`, `cmd.txt` -- the issue's own repro, unmodified (SPIR-V, as filed).
- `match.json` -- sanity-only `internal_failure` predicate; documented as not testing the
  actual (Valgrind-only) symptom.
- `out-main-debug.txt` -- primary probe, exit 0, no-repro (expected; see ask 1 discussion).
- `variant-dxil-main-debug.txt` -- DXIL-targeted control (`--expect no-match`), exit 0,
  corroborating `sudonatalie`'s comment that the shader also compiles fine to DXIL (no crash
  either way, on a non-instrumented build).
- `godbolt.txt` / skip reason recorded via `triage.py godbolt --skip` -- a Compiler Explorer
  link was deliberately not produced; see reasoning above (CE is Release-build, no Valgrind/MSan
  equivalent, so a clean-compile link would misleadingly read as "fixed").
