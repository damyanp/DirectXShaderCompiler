# DXC issue triage — batch 005

**Ground truth:** clean `main` **Debug** build, commit `ab5400907`
(`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`),
verified live from this session by running `dxc --version` and cross-checking it against
`triaged_with_commit` in all five `verdict.json` files and against the `compilers` table.
**History:** 20 official release binaries, v1.4.1907 → v1.9.2607.
**FXC comparisons:** real `fxc.exe` from Windows SDK 10.0.26100.
**Nothing was posted, edited, labelled or closed. No DXC source was modified**
(`git diff upstream/main..HEAD -- . ':(exclude).github/skills/**'` is empty).

> **The compiler changed between batches.** Batches 001–004 measured `eff900d5`; this batch
> measured `ab5400907`, a build made for it. Verdicts are not directly comparable across that
> boundary, and any claim below about an earlier batch's issue is a claim about `eff900d5`
> unless it says otherwise.

This is the **second batch under the parallel per-issue session model**, and the first run
under the rule that the collation session is briefed only by what is on disk. Batch 004
predicted this batch would be cheaper and said what it would mean if it were not; that
prediction is re-derived from scratch in
[§ 1 of what batch 005 taught us](#1-the-parallel-model-verdict-established-with-one-named-residual-risk).

## Headline

**Four of five still reproduce; one is unmeasurable from `main` and says so only in passing.**
None is closable. As in batch 004 the verdict distribution is the least interesting part, and
the batch earns its keep on three things.

**Batch 004's prediction about the `invalid-probe` classifier was correct, and worse than it
guessed.** It predicted the classifier would be least trustworthy on an issue whose reported
symptom is a *diagnostic*, because the signal ("this build rejected the input before reaching
the code under test") and the symptom (an error message) become the same observation. #3055 was
composed to test that and found the defect in **both directions**: a release emitting the good
diagnostic the issue asks for was demoted, so `bisect` would trim away the very release that
fixed it; and a probe that *matched* was demoted, so every release including ground truth would
be discarded and `bisect` would report `no release could run this repro` — a message that
misattributes the cause entirely. Both are fixed, narrowly, with tests.

**Two issues' own text now contradicts their behaviour, and a third's thread does.** #8725's
title scopes a defect narrower than it is; #8732 describes a silent miscompilation that is a
loud error everywhere it can be reached from; and #3055's thread carries a 2023 maintainer
comment saying "this compiles successfully now" *above* a body that was edited later and still
reproduces byte-identically back to v1.4.1907. The third shape had no way to be recorded —
`text_stale` was defined as title-or-body — so the field's definition was widened and #3055 now
carries it.

**Two related-not-duplicate findings, one of them pointing at an untriaged issue.** #2530 is a
neighbour of batch 004's #2188 in the same ICE-folding area but a different rule, measured by
running each issue's construct through the other's shape. #3259 is a neighbour of **#3251**,
which is open, untriaged, from the same reporter one day earlier, and still traps on `main` in
a *different* pass. `duplicate-of` still has zero rows across 25 issues, and correctly so.

## Summary

| # | Title | Repro | Status | History | Action | Link |
| --- | --- | --- | --- | --- | --- | --- |
| [#2530](https://github.com/microsoft/DirectXShaderCompiler/issues/2530) | Array bound with `static const` variable | complete | **repros** | always (all 20 releases, linear) | keep open | [Yzd9KjcaG](https://godbolt.org/z/Yzd9KjcaG) |
| [#3055](https://github.com/microsoft/DirectXShaderCompiler/issues/3055) | Improve error reporting for intrinsic methods | complete | **repros** | always; v1.4.1907 output **byte-identical** to `main` | keep open | [M7e5Yrr36](https://godbolt.org/z/M7e5Yrr36) |
| [#3259](https://github.com/microsoft/DirectXShaderCompiler/issues/3259) | Crash in `TranslatePtrIfUsedByLoweredFn` | complete | **repros** | always v1.5.2010+ (19); **not** an NDEBUG artefact | keep open | [8rxodd943](https://godbolt.org/z/8rxodd943) |
| [#8725](https://github.com/microsoft/DirectXShaderCompiler/issues/8725) | `HitObject::Invoke` payload by value asserts | complete | **repros** | always v1.8.2505+ (5 of 20 can express `lib_6_9`) | keep open | [Eo8YbKs5n](https://godbolt.org/z/Eo8YbKs5n) |
| [#8732](https://github.com/microsoft/DirectXShaderCompiler/issues/8732) | `SPV_EXT_descriptor_heap` mixed aliasing | partial | **inconclusive** | **unmeasurable** — filed against unmerged PR #8517 | human judgement | [bcn4zoTdM](https://godbolt.org/z/bcn4zoTdM) |

Confidence is `high` on all five. **`text_stale` is set on #3055, #8725 and #8732.** All five
CE links were fetched from `https://godbolt.org/api/shortlinkinfo/<id>` during collation and
resolve to the panes claimed. Drafts were written by `claude-sonnet-4.6` (#2530, #3055),
`claude-opus-4.6` (#3259, #8725) and `claude-opus-4.5` (#8732); all five were reviewed by
`gpt-5.6-sol`.

## Per-issue findings

### #2530 — a constant-expression rule, not an array-size rule

`float array[uint(ARRAY_SIZE)]` with `static const float ARRAY_SIZE = 4;` is rejected as a
variable-length array on every release from v1.4.1907 to v1.9.2607 and on `main`. FXC 10.1
accepts it.

The bound is not an integer constant expression under the C++03 ICE rules DXC inherited from
clang. `CheckICE` accepts an explicit cast **only when its operand is a `FloatingLiteral`**
(`ExprConstant.cpp:9317`), so `uint(<static const float>)` reaches `IK_NotICE` at `:9343`;
`BuildArrayType` then makes a `VariableArrayType` and `SemaType.cpp:2143` emits
`err_hlsl_vla`. Case 2 in the body (`static const uint ARRAY_SIZE_UINT = (uint)ARRAY_SIZE;`) is
the same rule one level out, via `VD->checkInitIsICE()`.

Two controls make it a rule rather than a guess: `float array[uint(1.0f)]` compiles (literal
operand), and a plain `static const uint` bound compiles (no cast at all). Dropping the cast
instead gives `err_array_size_non_int`, a different path — so the diagnostic is not
interchangeable either.

Clang's HLSL front end rejects both cases too, naming the constant-expression rule directly.
That makes this a language decision rather than a bug to fix quietly, and the draft says so.

### #3055 — the thread says it is fixed; it is byte-identical to 2020

`tex.Sample(SamplerComparisonState, float2)` lists only the 3-, 4- and 5-argument overloads and
never mentions the sampler type. The 2-argument overload — the one the user meant — is the only
one dropped.

`MatchArguments` computes `badArgIdx` (`SemaHLSL.cpp:5396`); the caller discards it
(`:11364-11369`) and returns a bare `TDK_NonDeducedMismatch` (`:11456`), whose note
`SemaOverload.cpp:9355-9360` elides under an explicit `HLSL Change`. So the information exists
and is thrown away one frame later. It is not `Sample`-specific: `GatherRed` behaves
identically.

All 20 releases were probed linearly and **v1.4.1907's output is byte-identical to `main`'s**.
FXC lists the candidate signatures showing `SamplerState`; `hlsl_clang_trunk` already emits
`no known conversion from 'SamplerComparisonState' to 'hlsl::SamplerState' for 1st argument` —
verified during collation by re-compiling the pane through CE's compile API, not taken from the
draft.

**The thread is the stale text here.** llvm-beanz commented on 2023-07-14 that it "compiles
successfully now"; the body was edited on 2023-09-27, i.e. *after*. A reader going top-down
meets a maintainer closing the question above a report that still reproduces. The comment is
about a different thing — the shader compiles once a valid overload is substituted — while the
filed complaint, that the diagnostic never names the sampler-type mismatch, is unchanged.

This issue is also where the classifier defect was found; see
[§ 2](#2-the-invalid-probe-classifier-breaks-on-diagnostic-shaped-symptoms-in-both-directions).

### #3259 — Debug-only assert, but *not* a Debug-only defect

`DXASSERT_NOMSG(Ty)` at `lib/DXIL/DxilUtil.cpp:877` in `hlsl::dxilutil::WrapInArrayTypes`, exit
`0x80000003`, reached from `TranslatePtrIfUsedByLoweredFn` — the frame in the title.
`GetLoweredUDT` returns `nullptr` for a struct with an embedded object type
(`HLLowerUDT.cpp:67`, and `:72` for the nested case), `ScalarReplAggregatesHLSL.cpp:426` does
not check it, and the null reaches `WrapInArrayTypes` at `:436`.

SKILL.md's `NDEBUG` warning primes a worker to expect "20 clean releases means nothing here".
**This is the converse and the worker checked rather than assuming.** `DXASSERT_NOMSG` expands
to `do { } while (0)` under `NDEBUG` (`include/dxc/Support/Global.h:369-371`), so the null type
flows on to `Builder.CreateAlloca(NewTy, ...)` at `:450` — and all 19 releases that support
`as_6_5` access-violate reading address 0. The release history is fully meaningful.

Two further results that the report does not contain: it is not `Texture2D`-specific (a
`SamplerState` payload asserts identically, and so does a `Texture2D` nested one level down),
and it is confined to `DispatchMesh` — `IsPtrUsedByLoweredFn`
(`ScalarReplAggregatesHLSL.cpp:310`) recognises only `IOP_DispatchMesh`'s payload operand, with
`TraceRay`, `ReportHit` and `CallShader` sitting next to it commented out under a
`TODO: Lower these as well`.

**v1.5.2010 crashes with completely empty stderr** while every later release prints
`Internal compiler error: access violation`. A predicate matching that text would have invented
a fix boundary at the release the issue was filed against.

### #8725 — the brief predicted no history; the worker measured one

Passing a payload to `dx::HitObject::Invoke` through an `in` (by-value) parameter asserts at
`CGCall.cpp:2962` (reference binding to unmaterialized r-value) and then emits
`bitcast %struct.Payload %v to %struct.Payload*`, which release builds turn into a DXIL
validation failure.

The asymmetry is in Sema. `AddHLSLIntrinsicMethod` (`SemaHLSL.cpp:6334-6340`) makes **every**
`inout` parameter of an object-method intrinsic an lvalue reference with no type guard, while
`AddHLSLIntrinsicFunction` (`SemaHLSL.cpp:2123-2135`) does so only when the type is neither an
array nor a record, or is a vector/matrix. Combined with the copy-in/copy-out temporary from
`EmitHLSLOutParamConversionInit`, the `CGCall` invariant breaks.

**`text_stale`:** the title says "passing a payload by value", but `dx::HitObject::TraceRay`
fails identically, and a mutable `static` payload passed straight to `Invoke` fails with no
by-value parameter and no user function at all. The generalisation beyond those two — an
object-method intrinsic with an `inout` record parameter and an argument whose address is not
provably non-aliasing — is explicitly recorded in the evidence as *a lead, not a measured
claim*, and the draft was corrected during review to say so.

**The brief for this issue predicted that history would be unmeasurable because SM 6.9 is new.
It was wrong and the worker proved it wrong**: SM 6.9 shipped in v1.8.2505, five of twenty
releases can express `-T lib_6_9`, all five reproduce, and a feature-presence control
(`control-hello.hlsl`) established that the other 15 are genuine feature absence rather than
some unrelated rejection. That distinction is now in SKILL.md as a rule; see
[§ 4](#4-invalid-probe-on-the-repro-is-ambiguous-a-feature-presence-control-resolves-it).

### #8732 — filed against a branch, and the report is stale in the other direction

The lowering this report describes belongs to PR #8517 and is not on `main`:
`descriptorHeapImageAliasVars`, `createDescriptorHeapIndexVar` and
`diagnoseDescriptorHeapAliasMixing` have zero occurrences in ground truth. The issue mentions
the PR only in passing, so anyone checking it against `main` or any release sees a loud
validation error and concludes it cannot be reproduced.

On `main` all five cases fail loudly and none is silent: defects 1–3 and the still-undiagnosed
heap-only conditional die on
`generated SPIR-V is invalid: [VUID-StandaloneSpirv-OpTypeImage-06924] Cannot store to OpTypeImage`,
and defect 4 on `UAV support not implemented with non-emulated heaps`. Re-run with `-Vd` the
module is semantically *correct* — both descriptors store into one `Function` image variable,
last store wins, `%boundTex` preserved — so `main` is illegal, not wrong.

**`text_stale` in two layers.** The title says "silent miscompilation or ICE", but the body's
own Actual Behavior section already says all four filed defects are now diagnosed and defect 4
no longer ICEs. Neither the title's state nor the body's is reachable from `main`.

Separately, the reporter's documented workaround (separate variables) compiles on v1.9.2607 and
now fails on `main` under the `UniformConstant` `ArrayStride` rule newly enforced by the
SPIRV-Tools `1c336172` bump (`ec2ba18da`), tracked as **#8740** — so every shader here that
actually indexes `ResourceDescriptorHeap` currently fails validation on `main`. (The stronger
claim in the first draft, that *no* `-fspv-use-descriptor-heap` shader validates at all, is
false and was corrected: a control that sets the flag without indexing the heap compiles,
exit 0. See [§ 10](#10-the-independent-review-earned-its-place-on-arithmetic-again).)

`inconclusive` + `needs-human-judgement` is right, but it undersells the finding. "Reported
against an unmerged branch" is a distinct shape and now has a rule in SKILL.md step 5.

## Cross-issue analysis

### Duplicates and relationships

**No duplicates. `duplicate-of` still has zero rows across 25 issues, and that remains
correct.** Two genuine relationships were established by measurement rather than by reading.

**#2530 ↔ #2188 (batch 004) — related, not duplicates.** #2530's thread contains exactly one
comment, pow2clk's *"Related to #2188"*, which is the pointer this collation was expected to
find from the artefacts. Both issues emit `err_hlsl_vla`, both are FXC-accepts-DXC-rejects, and
both are `CheckICE` gaps — but they fail different rules:

| | #2530 | #2188 |
| --- | --- | --- |
| construct | `uint(<static const float>)` | `<static const uint2>.x` |
| failing check | explicit cast is an ICE only if its operand is a `FloatingLiteral` (`ExprConstant.cpp:9317` → `IK_NotICE` at `:9343`) | a component of a `const` vector fails `isCXX11ConstantExpr` |

Rather than assert the distinction, #2188's construct was **run through #2530's shape**:
`data/issues/2530/crossref-vector-component.hlsl` puts
`static const uint2 SIZE2 = uint2(1,1); float array[SIZE2.x];` in a `ps_6_0` entry point with no
float and no cast anywhere in the bound, and it still fails
(`variant-crossref-vector-component-main-debug.txt`, exit `2147500037`,
`error: variable length arrays are not supported in HLSL`). Neither construct appears in the
other issue's repro, so fixing either leaves the other broken.

There is a real convergence underneath, worth recording for whoever fixes them: #2530 case 2
(`static const uint ARRAY_SIZE_UINT = (uint)ARRAY_SIZE;`) and #2188's `cThread` fail the *same*
final check — `VD->checkInitIsICE()` false at the `DeclRefExpr` case — differing only in why the
initializer is not an ICE. #2188's own `notes.md` reached the same conclusion independently in
batch 004 ("Not a duplicate … neighbouring cases of the same ICE-folding area"), from the other
side and without seeing #2530's evidence. Two isolated observers agreeing on a relationship is
stronger than either saying it twice.

**#3259 ↔ #3251 — related, not duplicates, and #3251 is untriaged.** @damyanp's 2024 comment on
#3259 says *"Note other AS related issue: #3251"*. #3251 is **open**, labelled `bug,crash`,
filed 2020-11-11 by the same reporter one day before #3259, with the same `as_6_5` +
`DispatchMesh` shape. Its repro was captured into #3259's directory
(`crossref-3251-cbuffer-payload.hlsl`) and still traps on `main` (`0x80000003`) — but in a
**different pass**:

| | #3259 | #3251 |
| --- | --- | --- |
| assert | `WrapInArrayTypes`, `DxilUtil.cpp:877` | `TranslateCBAddressUserLegacy`, `HLOperationLower.cpp` |
| pass | `SROA_Parameter_HLSL` | `DxilGenerationPass::GenerateDxilOperations` |
| trigger | payload contains an HLSL object type, so `GetLoweredUDT` returns `nullptr` | payload has no object type; `GetLoweredUDT` never returns `nullptr` |

Stack captured under `cdb` in `manual-case-crossref-3251-stack.txt`. Fixing #3259 will not fix
#3251. **#3251 is the strongest candidate for batch 006.**

**Everything else was checked and is not a relationship.** #3055 sits in the same
diagnostic-quality class as batch-001's #1306 and #1627 but shares no mechanism; #8725 and
#3259 share the shape "invalid HLSL reaches codegen and crashes instead of being diagnosed"
without sharing code; #8732 and batch-002's #3768 are both SPIR-V and otherwise unrelated.

**Issues named by batch-005 threads that are not triaged:** #3251 (above), #6464 (#8725 was
split out of it), #7761 and PR #7797 (`5678f17ee`, which added the
`SemaHLSL.cpp:7088-7097` check rejecting only `pType.isConstant(actx)`/`OK_BitField`), commit
`4f3e767f6` (#8726, a different crash), PR #8517 and #8740.

### Bearing on batches 001–004

- **#2188 (batch 004) should gain a cross-reference to #2530**, and vice versa. Neither draft in
  batch 004 could say this; #2188's draft already says "not a duplicate" in the abstract, and it
  can now be made specific.
- **#2202 (batch 004) has three stale variant headers.** They are `variant-hv-default-main-debug`,
  `variant-hv2021-main-debug` and `variant-vd-novalidate-v1.8.2403`, whose `# verdict:` lines say
  `no-repro` while today's code scores `invalid-probe`. This is a **finding produced by a fix made
  in this batch** — variants were never re-scored before, only their `--expect` was checked — and
  the three have been silently wrong since **batch 004**, when they were written (confirmed by
  `git log --diff-filter=A`: all three arrive in `fef93fdd1`), with their declared expectation
  (`invalid-probe`) satisfied the whole time by a header that said the opposite. The *latent
  defect* is older than that: `variant-*.txt` captures exist as far back as batch 001, so every
  variant written since then has gone unchecked. They were **not corrected here**, because
  batches 001–004 are out of scope; the correction is one command,
  `python scripts/triage.py reindex --accept`, and it changes no measurement. It should be the
  first thing batch 006 does.
- **No earlier verdict is believed to be wrong.** The #2202 headers are a derived field, not a
  conclusion; #2202's issue-level verdict is unaffected.

### Patterns across the five verdicts

1. **Three of five issues are stale in their own text, and in three different places** — title
   (#8725), title *and* body (#8732), thread (#3055). That is the highest rate in any batch, and
   it is what pushed `text_stale`'s definition to cover comments.
2. **Two of five would have been mis-triaged by a plausible shortcut.** #3259 by trusting the
   `NDEBUG` warning instead of checking the macro's expansion; #8732 by treating "does not
   reproduce on `main`" as an answer rather than as evidence that the wrong thing was measured.
3. **Every issue in this batch needed at least one control**, and on #8732 a control was the
   *only* thing that caught a vacuously-true absence clause. No amount of tooling can see that a
   `not_regex` naming a symbol is satisfied for free by a shader that never declares it.
4. **The two oldest issues are language/design questions, the two newest are Sema/codegen
   omissions.** Consistent with batches 001–004; still a sampling artefact, not a measurement.

## Proposed label changes

None are applied. All are recorded proposals, validated against the live taxonomy.

| # | Current | Proposed | Why |
| --- | --- | --- | --- |
| #2530 | `bug`, `fxc-disagrees` | add `check-in-clang` | Clang's HLSL front end rejects both cases and names the rule; the resolution is a language decision, which is exactly what that label routes |
| #3055 | `tech-debt`, `diagnostic` | no change | already correct |
| #3259 | `bug`, `dxil`, `crash` | no change | already correct |
| #8725 | `bug`, `needs-triage` | drop `needs-triage`; add `crash` | triaged here with a complete repro, a source diagnosis and a five-release history; the symptom is an assert |
| #8732 | `bug`, `spirv`, `needs-triage` | keep `needs-triage` | deliberately: it is filed against an unmerged branch and only a human can decide whether to retarget, park behind #8740, or close as branch-local |

## What batch 005 taught us about the method

### 1. The parallel model — verdict: **established**, with one named residual risk

Batch 004 predicted batch 005 would be "much cheaper" because three of its four defects were
*caused* by parallelism rather than revealed by it, and said that if it were not cheaper, "the
shared-state surface is larger than four fixes". The orchestrator's notes contain a table
claiming the prediction held. That table quotes batch 004's figures rather than re-checking
them and is grading its own homework, so everything below was re-derived in this session.

**Incidents, independently verified:**

| Batch 004 defect | Batch 005 | How this session checked it |
| --- | --- | --- |
| workers ran destructive `reindex` (5/5) | **0/5** | `reindex` at the start of collation reported **zero** preserved/restored fields, zero stale probes and zero re-scoring disagreements across 25 issues and 346 runs; all 25 issue rows still carry `title`, `url`, `created_at`, `labels` and `status` (only 3 lack `godbolt_url`, all documented `--skip`s from earlier batches). A destructive rebuild would have emptied exactly those columns |
| rows lost (#2191) | **none** | every batch still holds exactly 5 issues; `runs` rebuilds to **346**, which equals the count of `out-*.txt` on disk exactly |
| predicate/filename collisions (3/5 workers, ~20 captures lost) | **none** | #3055 ran four predicates and #8732 two, and every capture is correctly name-spaced (`out-<compiler>--<predicate>.txt`); no file is scored by a predicate other than the one in its header |
| out-of-batch directories modified (1) | **none** | `git status --porcelain` shows only the five new issue directories plus `data/reports/`, all untracked before this session |
| shared-state writes | **none** | `SKILL.md`, `README.md` and `scripts/` were untouched when collation began; all five `method-notes.md` record observations rather than edits |

**Cost, independently derived.** "Cheaper" turns out to be the wrong word, and the honest answer
needs both columns:

| | batch 004 | batch 005 |
| --- | --- | --- |
| primary release probes (`out-*.txt` = `runs` rows) | 87 | **126** |
| labelled controls/variants | 62 | 46 |
| hand-driven captures (`manual-*.txt`) | 20 | **10** |
| shaders committed | 30 | 33 |
| predicates | 8 | 9 |
| total files in the five issue directories | 274 | 272 |

Batch 005 produced **45 % more automated release probes and half as many hand-driven captures
for the same number of files**. It was not cheaper in compute; it was cheaper in *rework*. Batch
004's variant and manual counts are inflated by captures it had to redo after the collisions,
and none of batch 005's budget went there.

**So: established.** The discriminator batch 004 proposed was whether the next batch's defects
are *caused* by parallelism. Batch 005 found four tooling defects (§ 2–§ 5) and **none of them
is a parallelism defect** — every one would exist identically in a serial workflow. That is the
predicted outcome, from the predicted cause.

**The residual risk, named rather than waved away.** Batch 005 exercised the collision surface
slightly less than batch 004 did: two of five workers ran multiple predicates against one
issue, versus three of five. #3055's four predicates drove the exact path that broke in batch
004 and came out clean, so the fix is tested — but "0 incidents" rests on a smaller sample than
it looks. One more batch with several multi-predicate issues would close it. The model should
be treated as established and still watched, not as proven and forgotten.

### 2. The `invalid-probe` classifier breaks on diagnostic-shaped symptoms, in both directions (new)

Batch 004's prediction was right. `classify()` demotes a probe to `invalid-probe` when the
output matches a feature-absence marker, because "the compiler rejected the input before
reaching the code under test" is normally invisible to a symptom predicate. On an issue whose
symptom *is* a diagnostic, the marker and the symptom are the same observation. #3055 measured
both failures against real captures:

- **Direction A** (`triage.py:688` as it stood). `variant-methodology-freefn-main-debug--match-methodology-freefn.txt`
  is real dxc output: `error: no matching function for call to 'clamp'` plus the note naming the
  bad argument. That is a *good* diagnostic, and for a diagnostic-quality issue the correct score
  is `no-repro` — "fixed here". The runner returned `invalid-probe`, and `bisect` trims those, so
  a history search would **hide the very release that fixed the issue**.
- **Direction B** (`triage.py:711-713` as it stood). `variant-methodology-arity-main-debug--match-methodology-arity.txt`:
  dxc answers `error: use of undeclared identifier 'clamp'` for a wrong-arity call to a plainly
  declared intrinsic — itself a fileable diagnostic bug. The predicate *matched*, but
  `_is_absence_predicate` returns true if **any** sub-predicate of an `all_of` is absence-based,
  and #3055's mixed predicate trips it. Every release including ground truth would be discarded,
  and `cmd_bisect` would then exit with
  `no release could run this repro; retarget it at a profile/flag set the releases support` —
  misattributing the cause entirely.

**#3055's primary predicate escaped by one word.** dxc says `no matching **member** function for
call to` for intrinsic *methods*; the marker is `no matching function for call to`. The batch's
headline finding was one noun away from being invisible.

**The fix, and why it is this one.** The danger here is real and asymmetric: a more permissive
classifier reintroduces the fake-regression bug the markers exist to prevent, which has produced
wrong verdicts twice (#3873 at `ps_6_7`, #3038 at `use of undeclared identifier 'RayQuery'`), and
batch 004 already **rejected** the converse rule because #1627's reported symptom *is* an
`unrecognized argument` diagnostic. So the suppression is the narrowest thing that fixes both
directions:

> `classify` ignores a matched marker when a **positive** clause (`contains` or non-inverted
> `regex`) of the issue's own `match.json` contains that marker text verbatim.

That requires a human to have written the diagnostic in as the symptom, which is exactly the
case the proxy cannot handle, and nothing else. Inverted clauses do not count — "the symptom is
that X is absent" does not make X's presence a measurement. No predicate is evaluated as a regex
against the marker, so a loose pattern cannot widen it.

**#3055's alternative proposals were considered and not taken.** Its preferred fix was the same
overlap rule, so that one was adopted. Its third proposal — retire
`no matching function for call to` as "not a feature-absence signal at all" — was **rejected**:
a release predating a new *overload* of an existing intrinsic does answer exactly that, and the
markers that would replace it (`use of undeclared identifier`, `unknown type name`) only cover
wholly-absent symbols. Its second proposal, an explicit `"diagnostic_symptom": true` opt-out,
was not needed once the overlap rule was in place, and an opt-out nobody is forced to set is an
opt-out that gets forgotten.

**Evidence that it is narrow:** re-running `reindex` over all 25 issues and 346 archived runs
after the change moved **exactly the two probes that demonstrated the defect, and nothing
else**. Nine tests were added covering both directions, the near-miss (`member`) case, the
inverted-clause case, and all three historical fake-regression scenarios.

The two demonstration probes were captured `--expect invalid-probe` to document the defect.
Rather than retiring them — which their own `match-*.json` notes suggested — their expectations
were revised with `triage.py expect` to `match` and `no-match`, turning them into permanent
regression assertions that the fix stays fixed. No measurement was altered. This also closes the
`--expect` vocabulary gap #3055 raised: there is no longer any need for a value meaning "the
classifier is expected to get this wrong here".

### 3. `is not supported`, unqualified, is not a feature-absence signal (new — convergent)

#8732 noticed independently, and without being briefed on the classifier at all, that the bare
phrase `is not supported` collides with PR #8517's own diagnostic
`mixing bound and descriptor heap resources in the same variable is not supported with SPV_EXT_descriptor_heap`.
Checked against DXC source during collation: **the phrase appears in about 25 distinct
diagnostics**, most of them ordinary semantic errors about present-day code
(`operator is not supported`, `signed integer division is not supported on minimum-precision
types`, `payload access qualifiers … is not supported`, and the SPIR-V emitter's own errors).

Anchored to the target/profile/shader-model forms, which are the ones that really mean "this
build cannot express your input". It fired on **no archived capture**, so the anchoring changes
no existing verdict — it removes a trap rather than fixing a symptom.

**This is the batch's convergence result and it is worth weighting accordingly.** #3055 was
dispatched with a brief that named the classifier as a hazard; #8732 was not briefed on it at
all and arrived at the same function from the opposite end, on a completely different kind of
issue. Two isolated workers independently identifying the same defect in the *tooling* is much
stronger evidence than one worker saying it twice — batch 004 made this point as item 11, and
this is its second instance.

### 4. `invalid-probe` on the repro is ambiguous; a feature-presence control resolves it (new)

From #8725, whose brief predicted an unmeasurable history and was disproved.
`invalid-probe` on a repro can mean the release predates the feature, or that something
unrelated in the repro was rejected — and only the first justifies trimming that release out of
the history. The discriminator is the *smallest shader that uses the feature at all*, run under
the same profile and flags:

- `invalid-probe` on both repro and control → feature absence; trimming is correct.
- `invalid-probe` on the repro with a **clean** control → the rejection is about your repro, and
  trimming it silently hides a real result.

Now in SKILL.md step 6.

### 5. A brief may name a hazard; it must not predict the verdict (new)

Also from #8725. Its brief said history would be unmeasurable because `lib_6_9` is new. The
worker measured a full five-release history instead. A less careful worker would have recorded
the prediction as the result and **nothing on disk would have contradicted it** — the prediction
is not a probe, so `reindex` cannot see it and `audit` cannot see it. This is the one hazard in
the parallel model that no mechanical check can catch, and the only defence is not writing
expected outcomes into briefs. Now in SKILL.md's briefing section.

### 6. Variants' verdicts were never re-scored (new, and it found something)

`reindex` re-scored `out-*.txt` against today's predicate code and, for `variant-*.txt`, checked
only the declared `--expect`. So a control's own `# verdict:` line could disagree with the
current classifier indefinitely, silently, with no command able to correct it. Surfaced while
re-declaring #3055's two demonstration probes, and fixed by scoring variants the same way as
primaries.

**Its first run found three stale headers in #2202, wrong since batch 004** — see
[§ Bearing on batches 001–004](#bearing-on-batches-001004). A check that finds a real defect in a
signed-off batch on its first execution is the cheapest kind of evidence that it was worth
adding.

### 7. An `invalid-probe` verdict now says why, on disk (new)

`invalid-probe` is the one verdict that means "ignore this measurement", and `bisect` acts on it
by dropping the release. Reconstructing which of three independent rules fired, and on what
text, meant re-reading `classify()` against the whole capture — so the most consequential
verdict was the least self-explaining artefact in the tree. Raised by #3055 after doing exactly
that. Captures now carry `# invalid-probe-reason: …`, written by `run` and kept in step by
`reindex --accept`.

### 8. Four smaller tooling defects, all measured (new)

- **`ce_args()` kept the source file after any value-less flag.** It decided "is this token a
  flag's value?" by "did the previous token start with a dash", so `… -spirv repro.hlsl` handed
  Compiler Explorer a second, nonexistent input — #8732 had to write every pane by hand with an
  `id:<args>` override. Now uses the same `VALUE_FLAGS` table `retarget_cmd` uses (with
  `-include` added, which was missing from it and is a latent bug in `retarget_cmd` too).
- **`run --args` silently supersedes `cmd.txt`.** Used without `--label` it overwrites the
  *primary* capture with a command `cmd.txt` does not specify. `reindex` catches the mismatch,
  but `reindex` is collation-only, so on #3259 the primary capture sat stale for the length of
  the triage. `run` now warns at capture time.
- **`labels --refresh` died on a GraphQL rate limit** with an unhandled traceback while the REST
  budget still showed 4991/5000 (#8732). Now falls back to `gh api repos/<repo>/labels`.
- **`bisect` excluded prereleases silently**, and the catalogue held a nameless duplicate row for
  a release with an empty tag (#8725). `bisect` now names what it excluded before it starts, and
  `catalog` skips tagless releases. The junk row was deleted.

### 9. `text_stale` could not express a stale *comment* (new)

#3055's body is accurate; its **thread** is not. The field was documented as title-or-body, so
the finding had nowhere to go except prose — and `overview.md`, which sorts stale-text findings
to the top of their tier, would never have surfaced it. The definition now covers "a maintainer
comment left standing in the thread", because the harm is identical: a reader believes the issue
over the compiler. #3055 now carries the field, and `SKILL.md` and `README.md` both say which of
the three shapes to name.

### 10. The independent review earned its place on arithmetic, again

`gpt-5.6-sol` reviewed all five drafts and returned 19 suggestions. As in batch 004, **its best
output was not concision — it was counting**, and three of its findings were real errors that
five isolated workers and their own re-reads had missed:

- **#8732 said "all four cases".** The draft enumerates defects 1, 2, 3, the heap-only
  conditional *and* defect 4 — five. Confirmed against the five committed shaders. Fixed in the
  draft **and in `verdict.json`'s summary**, which had the same error and would have carried it
  into `overview.md`.
- **#8732 claimed "no `-fspv-use-descriptor-heap` shader validates on `main` at all".** False:
  `variant-bound-only-main-debug.txt` runs that flag set and **exits 0** with valid SPIR-V. The
  failure needs an actual `ResourceDescriptorHeap` use. Narrowed in the draft and in the verdict
  summary.
- **#8725 described `AddHLSLIntrinsicFunction`'s guard as "only if it is not an array or record
  type", omitting an arm.** The source is
  `if ((!Ty->isArrayType() && !Ty->isRecordType()) || hlsl::IsHLSLVecMatType(Ty))`.
- **#8725 overstated its own scope claim.** The evidence file's own §F labels the
  generalisation "stated as a lead, not a measured claim"; only `Invoke` and
  `HitObject::TraceRay` were measured. Scoped in the draft **and** in `text_stale`.

Accepted concision edits removed a preamble ("One note for anyone reading the thread
top-down: "), a hedge ("with no float and no conversion anywhere" → "in the bound"), a
standalone scaffolding line, an unsupported prediction about disabled code paths, and a
rhetorical flourish. One deletion — "Never worked." from #8725's history paragraph — was
accepted for a reason the reviewer got wrong: its stated justification was muddled and it
proposed no replacement, but the next two sentences state the history precisely, so the sentence
was redundant.

**Rejections, and why.** The reviewer's reliable failure mode is that it cannot see the
cross-issue evidence, because that evidence is held by collation and did not exist when the
drafts were written:

- **#2530 "fixing either leaves the other broken"** — flagged as an unsupported claim. It is
  measured: `variant-crossref-vector-component-main-debug.txt`. Kept.
- **#3259 "Fixing this one will not fix that one."** — same. Two different asserts in two
  different passes were captured. That sentence *is* the actionable output of a duplicate check;
  cutting it deletes the finding.
- **#8732 delete the `**Suggestions**` heading** — style preference; removing it blurs a section
  boundary in a long draft.

This is the second batch in which the review's value came from arithmetic rather than from
prose, and the second in which its concision suggestions were roughly half usable. Step 10's
instruction to demand quoted current text plus exact replacement text is what made the
accept/reject decision cheap; the two suggestions that arrived without a replacement were both
the weakest.

### Method claims rejected

- **"`-fsyntax-only` should be the *first* choice for front-end-diagnostic symptoms on a Clang
  pane, not a fallback" (#2530).** Over-general, and #3055 is the counter-example: its Clang pane
  does not use it and does not need it. The two workers appeared to contradict each other, and
  re-compiling both panes through CE's compile API during collation resolved it — #3055's failure
  is a hard Sema error (`no matching member function for call to 'Sample'`), so the backend never
  runs and the pane is already clean; #2530's is only a warning plus a note, so the compile
  proceeds into a DXIL backend that cannot lower `SV_Target` and the pane fills with noise about
  the stage. **The rule is whether the front end hard-errors**, and SKILL.md now says that rather
  than either worker's version.
- **"Strip ANSI SGR escapes in the harness" (#2530).** The escapes come from CE's `ce_compile`
  response, not from the local runner, and stripping them centrally would silently alter captured
  output — which the whole design treats as an observation. Per-pane `-fno-color-diagnostics`
  remains the right answer.
- **"`--linear` is cheap enough to default to when the repro fails fast" (#2530).** Not adopted
  as a default. #3259 makes the better version of the argument — the *shape* of failure across
  releases was itself part of the finding — but a default that costs 20 runs per issue is a
  default that will be turned off in a hurry on the first slow repro. SKILL.md's existing
  guidance (use it whenever the history mentions a fix, revert or re-opening) already covers the
  cases that matter, and #3259's reason is now recorded alongside it.
- **"Retire `no matching function for call to` from the marker set" (#3055).** Rejected; see
  § 2.
- **"`labels --refresh` should say whether it is per-issue or per-batch" (#8725).** Not a defect:
  the cache is global with an age warning, which is the correct granularity. No change.

## Proposed issue comments

These are **drafts for review, not posted**. No comment, label or state change
has been made on any issue. Each is written to be postable as-is by a maintainer, and every
claim in them is backed by captured evidence in `issues/<nnnn>/`.

They deliberately avoid promising fixes or timelines, and where the next step is a product or
language decision they say so rather than pre-empting it. Quoted compiler output was
re-verified before being written down.

Each draft ends with a trailer disclosing that it came from an assisted triage pass.

Source of each is `issues/<nnnn>/comment.md` — edit there, then re-run
`scripts/render_comments.py <batch>` to refresh this section.


### Draft — [#2530](https://github.com/microsoft/DirectXShaderCompiler/issues/2530) Array bound with static const variable

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2530](https://github.com/microsoft/DirectXShaderCompiler/issues/2530).

Both cases still reproduce on `main` (1.9.0.5433, `ab5400907`). Case 1 fails on
all 20 releases from v1.4.1907 through v1.9.2607, and case 2 was checked at both
endpoints and fails there too — v1.4.1907 (2019-07) is the oldest release
shipping a usable `dxc`, so that is as far back as it is possible to check. FXC
still accepts both.

**[Compiler Explorer: FXC / DXC 1.6.2112 / DXC trunk / clang](https://godbolt.org/z/Yzd9KjcaG)**

```
$ dxc -T ps_6_0 -E main repro.hlsl
repro.hlsl:7:16: error: variable length arrays are not supported in HLSL
    float array[uint(ARRAY_SIZE)] = { 1.0f };
               ^
```

### Where the line is drawn

The array and the `static const` are incidental. The bound is not an *integer
constant expression* under the C++03 ICE rules DXC inherited from clang, so the
declaration becomes a VLA:

| | |
| --- | --- |
| `float array[uint(ARRAY_SIZE)]`, `ARRAY_SIZE` a `static const float` | **error** |
| `float array[uint(1.0f)]` | compiles |
| `float array[ARRAY_SIZE]`, `ARRAY_SIZE` a `static const uint` | compiles |

`CheckICE` accepts an explicit cast only when its operand is a `FloatingLiteral`
(`tools/clang/lib/AST/ExprConstant.cpp:9317`); a `CK_FloatingToIntegral` applied
to a `DeclRefExpr` falls through to `IK_NotICE`, so `Sema::BuildArrayType`
builds a `VariableArrayType` and the HLSL check at
`tools/clang/lib/Sema/SemaType.cpp:2143` emits `err_hlsl_vla`. The second case
is the same rule one level out — `ARRAY_SIZE_UINT` is a const integral whose
*initializer* is not an ICE, so it cannot be used in one either. The
constant-expression evaluation is not HLSL-aware; only the diagnostic is.

Adjacent but not the same defect: dropping the cast (`float array[ARRAY_SIZE]`
with `ARRAY_SIZE` still `float`) takes a different path and gives
`error: size of array has non-integer type 'float'`.

### On "Related to #2188" — related, not the same defect

[#2188](https://github.com/microsoft/DirectXShaderCompiler/issues/2188) reaches
the same `err_hlsl_vla` from a different `CheckICE` case: a component of a
`const` vector. Measured here — `static const uint2 SIZE2 = uint2(1,1);
float array[SIZE2.x];` fails identically, with no float or conversion in the
bound:

```
crossref-vector-component.hlsl:16:16: error: variable length arrays are not supported in HLSL
    float array[SIZE2.x] = { 1.0f };
```

Neither construct appears in the other issue's repro, so **fixing either leaves
the other broken**. Same diagnostic, same FXC divergence, same area of
`CheckICE`; two rules.

### clang

clang's HLSL front end rejects both cases too, and names the cause:

```
<source>:7:22: note: read of non-constexpr variable 'ARRAY_SIZE' is not allowed in a constant expression
<source>:7:16: error: variable length arrays are not supported for the current target
```

That pane needs `-fsyntax-only`: clang's DXIL backend cannot yet lower a pixel
shader writing `SV_Target`, so without it a known-good control fails there too
and the pane says nothing about this issue. With it, the control compiles clean.

### Suggested labels

Keep `bug` and `fxc-disagrees` — FXC 10.1 compiles both cases and emits
`ps_5_0` code, verified in the link rather than taken from the report. Consider
adding `diagnostic`: the message reports a VLA, which HLSL does not have and
nobody here wrote, and names neither the conversion nor the constant-expression
rule. That is worth improving independently of whether HLSL's rules should
change to match FXC, which is a language decision this triage does not settle.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3055](https://github.com/microsoft/DirectXShaderCompiler/issues/3055) Improve error reporting for intrinsic methods with type mismatched arguments

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3055](https://github.com/microsoft/DirectXShaderCompiler/issues/3055).

Still reproduces on `main` (1.9.0.5433, `ab5400907`, Debug), and on **all 20 release binaries
from v1.4.1907 (2019-07) through v1.9.2607** — a full linear scan, not just the endpoints. The
v1.4.1907 output is byte-identical to today's, caret art included.

The "compiles successfully now" comment from 2023-07-14 refers to the *original* example,
which was replaced on 2023-09-27. The example currently in the body produces exactly the
output quoted beneath it.

**Repro:** <https://godbolt.org/z/M7e5Yrr36> (FXC · DXC 1.6.2112 · DXC trunk · `hlsl_clang_trunk`)

### The intended overload is the one candidate that is suppressed

Passing the *correct* `SamplerState` but one argument lists **four** candidates — requires 2,
3, 4, 5 arguments. The issue's shader lists **three** — 3, 4, 5. The 2-argument overload is the
only one dropped, so the notes describe only overloads that were never being called.

Not specific to `Sample`: `tex.GatherRed(samp, coord)` with the same mistake gives the same
shape — notes requiring 3, 4, 6 and 7 arguments, nothing about the sampler type.

### Where the note is dropped

`DeduceTemplateArgumentsForHLSL` selects candidates by argument count, then calls
`MatchArguments`, which computes `badArgIdx` — "The first argument to mismatch if any"
(`SemaHLSL.cpp:5396`). On mismatch the caller does `++cursor; continue;`
(`SemaHLSL.cpp:11364-11369`) and the value is discarded, so the loop falls out to a bare
`TDK_NonDeducedMismatch` (`SemaHLSL.cpp:11456`) with no `FirstArg`/`SecondArg`. `SemaOverload.cpp:9355-9360`
then elides the note explicitly:

```cpp
// HLSL Change Starts
// The implementation for template argument deducation does not yet provide
// FirstArg and SecondArg information for failure cases; ellide the note in
// this case.
if (FirstTA.isNull() || SecondTA.isNull()) return;
// HLSL Change Ends
```

The remaining notes come from candidates rejected on arity before deduction, which is why the
arity complaints are all that survives.

### Both comparison compilers name the type

FXC prints the candidate signatures, each showing `SamplerState` first:

```
error X3013: 'Sample': no matching 2 parameter intrinsic method
error X3013: Possible intrinsic methods are:
error X3013:     Texture2D<float4>.Sample(SamplerState, float2|half2|min10float2|min16float2)
```

`hlsl_clang_trunk` already emits the wanted note:

```
note: candidate function not viable: no known conversion from 'SamplerComparisonState' to 'hlsl::SamplerState' for 1st argument
```

Controlled: with `SamplerState samp` the Clang pane produces no overload error at all and
fails later in DXIL lowering, which the repro never reaches. Clang's HLSL front end already
emits the note this issue asks for.

**Labels** — suggest adding `fxc-disagrees` (measured above) and `usability` (plausible slip,
misdirecting message). `tech-debt` and `diagnostic` still fit; nothing to remove.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3259](https://github.com/microsoft/DirectXShaderCompiler/issues/3259) Crash in TranslatePtrIfUsedByLoweredFn 

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3259](https://github.com/microsoft/DirectXShaderCompiler/issues/3259).

**Still reproduces** on `main` (`1.9.0.5433 (triage, ab5400907)`), Debug build, on the shader
exactly as filed:

```
$ dxc -T as_6_5 -E main repro.hlsl
Internal compiler error: Terminal Error 0x80000003     # exit 0x80000003
```

The `DXASSERT` text only reaches `OutputDebugString`, so under a debugger:

```
Error:  !(Ty)
File:   lib\DXIL\DxilUtil.cpp(877)
Func:   hlsl::dxilutil::WrapInArrayTypes
  dxcompiler!hlsl::dxilutil::WrapInArrayTypes+0x5f
  dxcompiler!TranslatePtrIfUsedByLoweredFn+0x266
  dxcompiler!SROAGlobalAndAllocas+0x7b1
  dxcompiler!SROA_Parameter_HLSL::runOnModule+0x8a7
```

The debug flags in the report are not load-bearing — `-Zi -enable-16bit-types -Qembed_debug`
make no difference; they are dropped here so old releases have fewer ways to reject the input.

**It is not assert-only, so it is not confined to Debug builds.** All 19 releases that support
`as_6_5` — v1.5.2010 (2020-10, three weeks before this was filed) through v1.9.2607 — take an
access violation on the same input:

```
$ dxc -T as_6_5 -E main repro.hlsl
Internal compiler error: access violation. Attempted to read from address 0x0000000000000000
                                              # exit 0xC0000005
```

v1.4.1907 is the only release that does not crash, and only because it predates the profile
(`error: invalid profile as_6_5`). v1.5.2010 crashes with **no message at all** — of the
releases tested, v1.6.2104 is the first that prints that "Internal compiler error" line.
[Compiler Explorer](https://godbolt.org/z/8rxodd943) shows the Linux face of the same fault:
`dxc_1_6_2112` and `dxc_trunk` both terminate with `SIGSEGV`. Those are Release builds, so they
cannot show the assert; what they show is that removing the assert does not remove the bug.

**@jeffnn's 2020 diagnosis still holds.** `GetLoweredUDT` returns `nullptr` for a
struct with an embedded object (`HLLowerUDT.cpp:67`, and `:72` for the nested case);
`ScalarReplAggregatesHLSL.cpp:426` does not check it; `Ty != NewTy` is therefore true and the
null reaches `WrapInArrayTypes` at `:436`, which is where the assert fires. With `NDEBUG` that
assert is compiled out (`DXASSERT_NOMSG` → no-op) and the null type flows on to
`Builder.CreateAlloca(NewTy, ...)` at `:450` — hence the read from address 0 in the releases.

**It is not `Texture2D`-specific, and nesting does not avoid it.** A `SamplerState` payload
asserts identically, as does a `Texture2D` one level down inside a nested struct — the latter
through `GetLoweredUDT`'s recursive `return nullptr` at `HLLowerUDT.cpp:72`. The check that
rejects the field is `dxilutil::IsHLSLObjectType`. Replacing the member with a `uint` compiles
cleanly on `main` and on both ends of the release range (v1.5.2010, v1.9.2607).

**It is specific to `DispatchMesh`.** `IsPtrUsedByLoweredFn` (`ScalarReplAggregatesHLSL.cpp:310`)
recognises only `IOP_DispatchMesh`'s payload operand; the `TraceRay`, `ReportHit` and
`CallShader` cases sit next to it commented out under a `TODO: Lower these as well`. Nothing
else reaches the unchecked `GetLoweredUDT` call through this path today; enabling those three
would.

**On the "other AS related issue", [#3251](https://github.com/microsoft/DirectXShaderCompiler/issues/3251)
— related, not a duplicate.** Its repro still traps on `main` too (exit `0x80000003`), but in a
different assert in a different pass: `TranslateCBAddressUserLegacy` (`HLOperationLower.cpp`),
reached from `DxilGenerationPass`, not `WrapInArrayTypes` from `SROA_Parameter_HLSL`. Its payload
holds no HLSL object type, so `GetLoweredUDT` never returns `nullptr` and this issue's path is
never entered. Fixing this one will not fix that one.

Suggested label: add **`incorrect-code`** ("Issues relating to handling of incorrect code") —
the input is invalid HLSL that should be diagnosed, and the defect is that it crashes instead.
`bug`, `dxil` and `crash` all still fit.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#8725](https://github.com/microsoft/DirectXShaderCompiler/issues/8725) [SER] Passing a payload by value to HitObject::Invoke asserts in CodeGen

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#8725](https://github.com/microsoft/DirectXShaderCompiler/issues/8725).

Reproduces on `main` (`1.9.0.5433 (triage, ab5400907)`), exactly as reported, and on every
release that can compile the shader at all. Compiler Explorer, annotated:
<https://godbolt.org/z/Eo8YbKs5n>

**The assert.** `-T lib_6_9` on the repro exits `0xE0000001`. The first assert to fire is the
one you noted as "preceding" — it is the primary failure, not a side effect:

```
Error: assert(type->isReferenceType() == E->isGLValue() && "reference binding to unmaterialized r-value!")
File:  tools/clang/lib/CodeGen/CGCall.cpp(2962)
Func:  clang::CodeGen::CodeGenFunction::EmitCallArg
```

`CGMSHLSLRuntime::EmitHLSLOutParamConversionInit` (`CGHLSLMS.cpp:6185`) inserts a
copy-in/copy-out temporary for `Invoke`'s `inout` payload, then rewrites the argument to a
`DeclRefExpr` built with **`VK_RValue`** because the payload is an aggregate
(`CGHLSLMS.cpp:6384-6392`, "Aggregate type will be indirect param convert to pointer type. So
don't update to ReferenceType, use RValue for it."). `EmitCallArg` then sees `type` =
`Payload &` from the callee prototype against a non-glvalue expression, and the assert at
`CGCall.cpp:2962` is precisely that mismatch. Continuing past it lands in the by-value
aggregate path — `CreateLoad` at `CGCall.cpp:3411`, `CreateBitCast` at `CGCall.cpp:3429` —
which is where your `"Invalid cast!"` comes from.

**The emitted IR, which makes the release-build face self-explanatory.** `-fcgl` succeeds and
prints:

```llvm
%14 = load %struct.Payload, %struct.Payload* %2
%15 = bitcast %struct.Payload %14 to %struct.Payload*
call void @"dx.hl.op..void (i32, %dx.types.HitObject*, %struct.Payload*)"(
    i32 382, %dx.types.HitObject* %obj, %struct.Payload* %15)
```

A struct value bitcast to a pointer. With `inout` the parameter lowers to
`%struct.Payload* noalias %p`, `SafeToSkip` holds (`CGHLSLMS.cpp:6355`), no temporary is
created and the pointer is passed straight through — which is why the workaround works. A
plain local payload passed straight to `Invoke` takes the same path via the alloca case
(`CGHLSLMS.cpp:6347`), which is why SER is not broken for everyone.

**Why plain `TraceRay` is fine — a Sema asymmetry, and this is the actionable part.** Not the
intrinsic table: `gen_intrin_main.txt` says `inout udt Payload` for the free function
`TraceRay` (:311), for `Invoke` (:1141) and for `HitObject::TraceRay` (:1140) alike. The
difference is in the two functions that build intrinsic declarations:

- `AddHLSLIntrinsicFunction` (`SemaHLSL.cpp:2102`), for free functions, makes an `out`/`inout`
  parameter an lvalue reference only if it is **neither an array nor a record type**, or is a
  vector/matrix (`SemaHLSL.cpp:2123-2135`) — *"Aggregate type will be indirect param convert to
  pointer type. Don't need add reference for it."* `Payload` is a plain record, so
  `TraceRay`'s payload stays `Payload`.
- `AddHLSLIntrinsicMethod` (`SemaHLSL.cpp:6296`), for object/class methods, makes **every**
  `out`/`inout` parameter an lvalue reference (`SemaHLSL.cpp:6334-6340`), with no such guard.
  `dx::HitObject::Invoke` is a `[[static,class_prefix]]` method, so its payload is `Payload &`.

That is precisely the term the assert tests:

```
TraceRay   type = Payload     ->  isReferenceType() false == isGLValue() false   holds
Invoke     type = Payload &   ->  isReferenceType() true  != isGLValue() false   asserts
```

`-fcgl` bears it out: the `TraceRay` case builds the same copy-in/copy-out temporary but passes
its **address**, while the `Invoke` case materialises a second aggregate temp and then loads and
bitcasts it. So the temporary alone is not the defect — **it takes the temporary and a
reference-typed parameter together**, and each clean spelling is missing exactly one of the two.

**The title understates the scope.** Two variants fail identically, with the same assert at the
same line:

- `dx::HitObject::TraceRay(RTAS, …, ray, p)` with the same by-value `p`. Not `Invoke`-only.
- A mutable `static Payload g` passed straight to `Invoke` from the entry point — **no by-value
  parameter and no user function involved.** A mutable global is not an alloca, not
  groupshared and not a `noalias` argument, so it takes the same copy-in path.

So the trigger is broader than "passed by value": what both failing cases have in common is an
object-method intrinsic with an `inout` record parameter, called with an argument whose address
is not provably non-aliasing. `Invoke` and `HitObject::TraceRay` are the two that were measured;
other object methods built by the same path were not enumerated. Your other two observations
both check out: plain `TraceRay` with a by-value payload compiles clean (exit 0,
for the Sema reason above), and `-disable-payload-qualifiers` with no `[raypayload]`
annotations still asserts.

**History.** v1.8.2505 is the first release that can express this at all; every
release from v1.8.2505 through v1.9.2607 shows the release-build face verbatim
(`Instructions must be of an allowed type` at an `unreachable`). All 15 older releases answer
`error: invalid profile lib_6_9` — feature absence, not a clean run; v1.4.1907 and v1.8.2502
reject a trivial `lib_6_9` shader containing no SER at all in the same way. There is no window
to bisect.

**On the fix.** Your reading of the
existing guard is right: for `out`/`inout`/`ref` intrinsic parameters,
`HLSLExternalSource::MatchArguments` (`SemaHLSL.cpp:7093`) rejects only `pType.isConstant()` or
an `OK_BitField` argument — an `in` parameter is neither, and neither is a mutable global.
Separately, giving `AddHLSLIntrinsicMethod` the same record-type guard `AddHLSLIntrinsicFunction`
has would stop the assert, but on its own it would make the by-value case compile *silently*,
writing the payload back into a copy the caller never sees. Which of those to do, and whether
the static-global case should be diagnosed at all or simply lowered correctly, is a language
decision rather than something this triage can settle.

Label suggestion: add `crash` (it is an assert/ICE, so `bug` alone understates it),
`incorrect-code` (invalid input DXC fails to diagnose), `diagnostic` (the ask is a Sema error),
`sm6.9`; remove `needs-triage`. Not proposing `correctness` — the correct outcome is rejection,
not different codegen. We may be missing history behind the current labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

### Draft — [#8732](https://github.com/microsoft/DirectXShaderCompiler/issues/8732) [SPIR-V] SPV_EXT_descriptor_heap mixed bound/heap aliasing causes silent miscompilation or ICE

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#8732](https://github.com/microsoft/DirectXShaderCompiler/issues/8732).

**The lowering this report describes is not on `main` — it belongs to PR #8517.** Checked
against `main` at `13730886e` — built on a local branch, so the binary self-reports
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433` — and against every release
back to v1.4.1907. None of the named symbols exist on `main`: `descriptorHeapImageAliasVars`,
`descriptorHeapBufferAliasVars`, `createDescriptorHeapIndexVar`,
`tryToAssignDescriptorHeap{Image,Buffer}Alias`, `emitDescriptorHeapImageTexelPointer`,
`diagnoseDescriptorHeapAliasMixing`. `main` lowers `ResourceDescriptorHeap[i]` at the point of
use in `SpirvEmitter::doCXXOperatorCallExpr` (`SpirvEmitter.cpp:6642`) and hands back an
ordinary SSA value — there is no per-`VarDecl` alias state to go stale.

**On `main` all five cases fail loudly, and none of them is silent.** Defects 1, 2, 3 and the
undiagnosed heap-only conditional:

```
fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-OpTypeImage-06924]
Cannot store to OpTypeImage, OpTypeSampler, OpTypeSampledImage, or
OpTypeAccelerationStructureKHR objects
  OpStore %29 %30
```

and defect 4: `error: UAV support not implemented with non-emulated heaps.` No crash or
assert on a Debug build, so the "or ICE" half of the title is not observable here either.

The VUID-06924 failure is **not** about mixing: `Interlocked*` needs `OpImageTexelPointer`,
which needs a pointer to an image *variable*, so `main` stores the heap handle into a
`Function` image variable — illegal, and un-promotable by `mem2reg` precisely because
`OpImageTexelPointer` takes its address. A control with no bound resource at all fails
identically. `Interlocked*` on a heap-loaded texture is simply unsupported on `main`.

**`main` is not miscompiling underneath the validator.** Re-run with `-Vd`, the module is what
the source asked for — both descriptors stored into the same variable, last store wins, and
`%boundTex` still present and still in `OpEntryPoint`:

```
     %29 = OpVariable %_ptr_Function_type_2d_image Function
     %30 = OpLoad %type_2d_image %boundTex
           OpStore %29 %30
     %36 = OpUntypedAccessChainKHR … %resource_heap %uint_1
           OpStore %29 %37
     %40 = OpImageTexelPointer %_ptr_Image_uint %29 %39 %uint_0
     %41 = OpAtomicIAdd %uint %40 %uint_1 %uint_0 %uint_1
```

Illegal, not wrong.

[**Compiler Explorer**](https://godbolt.org/z/bcn4zoTdM) — three panes: DXC 1.9.2607 and
trunk showing the fatal error, and trunk with `-Vd` showing the module above. Read the third
pane, not the first two: a reader who sees only the errors will conclude something different
from what is actually happening.

**History is unmeasurable, and that is not a fix.** All 20 releases from v1.4.1907 to
v1.9.2607 were probed; 19 answer `dxc failed : Unknown argument: '-fspv-use-descriptor-heap'`.
Only v1.9.2607 runs the repro, and it matches `main` exactly, same VUID. One usable data point
is not a history.

**One thing that has changed on `main` since this was filed.** The workaround in the report —
separate variables for bound and heap-loaded resources — compiles cleanly on v1.9.2607 but
now fails on `main`:

```
fatal error: generated SPIR-V is invalid: Array must be explicitly laid out with
ArrayStride or ArrayStrideIdEXT decorations. … in the UniformConstant storage class
  %_runtimearr_type_2d_image = OpTypeRuntimeArray %type_2d_image
```

That is the SPIRV-Tools update in ec2ba18da (→ `1c336172`) newly enforcing explicit layout on
`UniformConstant` arrays, already tracked as #8740. `-fvk-use-scalar-layout` does not help.
While #8740 is open, every shader here that actually indexes `ResourceDescriptorHeap` fails to
validate on `main`, so this issue cannot be re-measured there even after #8517 lands. (A
control with `-fspv-use-descriptor-heap` set but no heap indexing still compiles, exit 0.)

**Suggestions**

- The title and body disagree: the title says "silent miscompilation or ICE", while *Actual
  Behavior* says all four defects are now diagnosed and defect 4 no longer ICEs. Only the
  heap-only conditional assignment is still described as silent. Worth retitling, and worth
  stating up front that this is against #8517's branch — otherwise anyone checking it against
  `main` or a release sees a loud validation error and concludes it cannot be reproduced.
- Consider whether this belongs as review feedback on #8517 rather than as a standalone
  issue, and whether the residual heap-only conditional case — the one part still described as
  undiagnosed, needing dataflow analysis rather than the per-variable state check — should be
  tracked on its own.
- Labels: add `correctness` (the reported defect is wrong code, and nothing currently records
  that). Note `incorrect-code` is about *handling* invalid input and does not apply. No
  removals proposed; there may be history here that this triage cannot see.

The report's own analysis held up where it could be checked here: the call sites, the
per-resource-class consumption points, and the aside that an `OpPhi` of image type fails
independently of descriptor heaps — that last one reproduces with a conditional between two
bound textures and no heap flag: `fatal error: generated SPIR-V is invalid: Result type cannot
be OpTypeImage`. The reported defect itself could not be checked, since it is not reachable
from a build of `main`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- **Sampling is deliberately unrepresentative, and this batch doubly so.** Three issues were
  chosen to test the `invalid-probe` classifier against diagnostic-shaped and feature-gated
  symptoms, which is the opposite of a random sample. Four of five reproducing tells you about
  the selection, not about the backlog.
- **Ground truth moved between batch 004 and batch 005** (`eff900d5` → `ab5400907`). No verdict
  in this report is directly comparable to one in batches 001–004.
- **#8732's reported defect was never measured, and cannot be from `main`.** Everything in its
  draft is either about `main`'s behaviour or about what is absent from `main`. The PR #8517
  branch was **not** built or tested; an earlier draft implied otherwise and was corrected.
- **#8725's wider-trigger generalisation is a lead, not a measurement.** `Invoke` and
  `HitObject::TraceRay` were measured. Other object-method intrinsics built by the same Sema path
  were not enumerated.
- **#3259's claim that release builds crash rests on source inspection plus 19 release probes**,
  not on a Release build with asserts enabled — those do not ship. The `NDEBUG` expansion
  (`Global.h:369-371`) and the `CreateAlloca` at `:450` are cited so the reasoning can be checked.
- **#2530's FXC comparison used FXC 10.1 from the Windows SDK**, which is not the FXC the 2019
  reporter used.
- **The bisection floor is v1.4.1907.** #2530, #3055 and #3259 all predate or straddle it, so
  "always reproduced" means "for as long as it is possible to check". For #3259 the effective
  floor is v1.5.2010, the first release with `as_6_5`.
- **No `--repeat` hit rate is quoted anywhere in this batch**, so SKILL.md step 5's rule that a
  quoted rate must be countable from a file in the issue directory is satisfied vacuously. All
  five repros are deterministic.
- **Two `# expect:` declarations were revised and two `# verdict:` headers restamped during
  collation**, both on #3055's demonstration probes, using `triage.py expect` and
  `reindex --accept`. No captured output, command line or exit status was altered. `#2202`'s
  three stale headers were deliberately left alone as out of scope.
- **`overview.md` is generated and was regenerated last.** `audit`'s staleness gate was checked
  first and does work — it failed at the start of this session because the overview predated
  #8725's `verdict.json`.

## Suggested next step

1. **Run `python scripts/triage.py reindex --accept` as the first action of batch 006** to clear
   #2202's three stale variant headers, which this batch found but left as out of scope. A
   permanent list of known-stale lines is where the next real disagreement hides.
2. **Triage #3251.** It is open, untriaged, from the same reporter as #3259 one day earlier, and
   still traps on `main` in a different pass. The evidence is already captured in
   `data/issues/3259/`. It is also the closest this workflow has come to needing `duplicate-of`,
   and it turned out not to be one — which makes it a good test of whether the distinction holds
   up when someone else re-derives it.
3. **Compose a batch with several multi-predicate issues.** The one residual doubt about the
   parallel model is that batch 005 exercised the predicate-collision surface on two of five
   issues rather than three of five. That is the last piece of evidence the model is missing.
4. **Give one issue to a worker with no hazard brief at all.** #8725's brief predicted its
   verdict and was wrong; #8732's worker found the classifier defect with no brief about it. It
   is worth measuring whether the hazard briefs are helping or anchoring.
