# DXC issue triage — batch 015

**Ground truth:** local Debug build `main-debug`, DXC `1.9.0.5433`, built from
public commit
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e).

**Nothing was posted, edited, labelled, closed or reopened on GitHub. No DXC
compiler source was modified, and no commit or push was made.**

> [!IMPORTANT]
> **Sampling bias:** these ten issues are among the oldest open DXC issues.
> They are enriched for long-lived behaviour, dormant enhancements and issue
> text whose context has aged. Their verdict mix, subsystem mix and closure
> rate do not generalise to the backlog.

## Headline

- All ten issues still reproduce, all at high confidence. There is no
  `close-fixed` recommendation in this batch.
- Four are best treated as enhancements rather than bugs: 4307, 4341 and
  4501 request missing capabilities or diagnostics; 4497 is correct but
  suboptimal code generation. The remaining six are live defects.
- The highest-value text warning is 4307: the body's final `out`-parameter
  claim is contradicted by `main` and all 18 releases tested for that
  `ms_6_6` variant.
- 4501's title still names `-Fd`, but current SPIR-V compilation rejects that
  flag. The capability request remains valid; its present-day shape is broader
  than the title suggests.
- Six verdict files carry the wrong batch identifier, and seven of ten
  `triaged_by` values disagree with the orchestrator's dispatch record. Those
  metadata errors do not change the technical verdicts, but they do break
  batch rendering and provenance.

| Issue | Verdict / repro | History | Recommendation | CE |
| --- | --- | --- | --- | --- |
| [4307](https://github.com/microsoft/DirectXShaderCompiler/issues/4307) | `repros` / complete | every mesh-capable release: v1.5.2010 at `ms_6_5`, then 18 releases at `ms_6_6` | enhancement; keep open | [Prfo6ssE7](https://godbolt.org/z/Prfo6ssE7) |
| [4341](https://github.com/microsoft/DirectXShaderCompiler/issues/4341) | `repros` / partial | all 16 stable releases supporting HLSL 2021 | enhancement; keep open | [Y5d6e1r16](https://godbolt.org/z/Y5d6e1r16) |
| [4350](https://github.com/microsoft/DirectXShaderCompiler/issues/4350) | `repros` / complete | all 20 stable releases | keep open | [TEcGjnve7](https://godbolt.org/z/TEcGjnve7) |
| [4351](https://github.com/microsoft/DirectXShaderCompiler/issues/4351) | `repros` / complete | all 19 releases with the rewriter option surface | keep open | n/a — `dxr.exe`/rewriter surface |
| [4384](https://github.com/microsoft/DirectXShaderCompiler/issues/4384) | `repros` / complete | all 20 stable releases | keep open | [rMsGE4K4s](https://godbolt.org/z/rMsGE4K4s) |
| [4415](https://github.com/microsoft/DirectXShaderCompiler/issues/4415) | `repros` / complete | 16 stable compiler releases; all 6 releases shipping `dxv.exe` accept the doctored module | keep open | [156dMcvPv](https://godbolt.org/z/156dMcvPv) |
| [4486](https://github.com/microsoft/DirectXShaderCompiler/issues/4486) | `repros` / complete | all 19 stable releases with SPIR-V codegen | keep open | [dYWfKGE1o](https://godbolt.org/z/dYWfKGE1o) |
| [4492](https://github.com/microsoft/DirectXShaderCompiler/issues/4492) | `repros` / complete | defect present in every release; reporter shader reaches it from v1.6.2104 | keep open | [3Pe367EfM](https://godbolt.org/z/3Pe367EfM) |
| [4497](https://github.com/microsoft/DirectXShaderCompiler/issues/4497) | `repros` / complete | same `test1`/`test2` asymmetry on all 20 stable releases | performance enhancement; keep open | [acfEvEz6o](https://godbolt.org/z/acfEvEz6o) |
| [4501](https://github.com/microsoft/DirectXShaderCompiler/issues/4501) | `repros` / agent-constructed | never implemented in all 16 releases able to emit the relevant instruction set | enhancement; keep open | [cj44aEcbj](https://godbolt.org/z/cj44aEcbj) |

## Text that no longer matches behaviour

> [!CAUTION]
> These are the spot-check traps most likely to produce a false
> “cannot reproduce” conclusion.
>
> - **4307 — body:** its final paragraph says the vague error also occurs when
>   a mesh-output member is passed to an `out` parameter. The mechanically
>   derived `out float` case compiles cleanly on `main` and all 18
>   `ms_6_6` releases; passing the whole element to `out Vertex` gets the good
>   source diagnostic. Only `inout`, which also reads, reproduces the vague
>   validator error. This is recorded in `text_stale`.
> - **4501 — title/premise:** “with `-Fd` flag” no longer describes an
>   available SPIR-V path. Current DXC rejects `-Fd` with `-spirv`; the oldest
>   relevant release accepted the option but then failed while looking for a
>   DXIL debug part. The live request is split SPIR-V debug information, not
>   merely two instructions added to an existing `-Fd` path.
> - **4384 — body symptom form:** the title remains exact, but current builds
>   report deterministic `unknown conversion kind` rather than the varying
>   illegal-memory read described in 2022. The two oldest releases still have
>   the reported silent access-violation face, so this is a moved symptom, not
>   a `text_stale` finding.

4497's title, `struct value on "stack"`, is vague but not false: `-fcgl`
contains the whole-struct `alloca` and copy that explain the issue. Its body and
comments still match current behaviour.

## Evidence verification and factual corrections

The release histories were re-counted from the `out-*.txt` headers and the
generated matrices, rather than copied from the notes:

- 4307: 18 primary release captures reproduce at `ms_6_6`; v1.4.1907 and
  v1.5.2010 are invalid for that profile. The separate matrix establishes the
  v1.5.2010 `ms_6_5` result and reports both self-tests as 18/20.
- 4341: the primary predicate is 16 reproductions plus four honest
  `invalid-probe` rows; the mirror “write landed” predicate is 16 negatives
  plus the same four invalid rows.
- 4350: 20/20 release captures reproduce. Its generated matrix reports
  80/80 expected probe/control outcomes.
- 4351: the purpose-built rewriter matrix has one invalid release and
  19 reproductions, with the non-array control negative on every row.
- 4384: 20/20 primary captures fail internally. The diagnostic control emits
  the wanted base-type error and the valid-enum control compiles on all
  21 builds.
- 4415: 16 compiler releases accept the invalid handle from the first stable
  release with the working descriptor-heap path; all six archived releases
  that ship `dxv.exe` accept the doctored module.
- 4486: 19/19 SPIR-V-capable releases retain two loops in the repro and zero
  in the workaround; the oldest release fails the anchor on all six cases.
- 4492: the reporter shader is negative on the two oldest releases because it
  takes a different lowering path. The minimal matrix is positive on all
  20 releases, while both load and store controls remain at a 32-byte span.
- 4497: the comparative matrix contains 21 builds, zero unexpected scores:
  `test1` reproduces and `test2` does not on every row.
- 4501: 21 binaries were parsed in the extended matrix; 19 produce SPIR-V in
  at least one mode, 16 stable releases emit the relevant instruction set,
  and none emits either requested instruction.

The independent draft pass found and applied these corrections:

1. **4307:** “Dropping `/Od` changes nothing” is broader than the captured
   evidence. The no-`/Od` variant was measured on v1.9.2607; the statement
   should be scoped to that release. The draft also repeats its entire labels
   paragraph.
2. **4350:** “matching on exit status alone reports it fixed” is imprecise.
   The counterfactual shows that the known-internal-status set without text
   markers invents a v1.7.2207 fix. Bare nonzero exit happens to classify all
   probe rows correctly, but also fires on the ordinary syntax-error control,
   so it is still an invalid predicate.
3. **4384:** “in every combination tried” should name the actual checks: the
   filed flag set and explicit HLSL 2018/2021 variants. Its extra footer about
   the local build identifier is redundant with the public ground-truth
   citation.
4. **4501:** “a build hash from the private tree” is unsupported wording. The
   evidence establishes a fork-local build identifier, not that the tree was
   private.
5. **Batch-014 cross-check:** 4256's note says `dxv.exe` first shipped in
   v1.8.2505, but the unpacked v1.8.2502 release contains `dxv.exe` for x86,
   x64 and arm64. The x64 file is 194,592 bytes, reports file version
   1.8.2502.8, and has a valid Microsoft Authenticode signature. The 4415
   matrix executes that exact file. Therefore v1.8.2502 is the verified floor;
   the older report was not edited in this collation.

Two metadata error classes were also verified mechanically:

- `verdict.json` says batch 012, 014 or 016 for **six** of these ten issues.
  The database therefore gives batch 015 only four rows.
- All workers were dispatched on `claude-opus-5`, but **seven** verdicts
  self-report another model. Across the current database there are
  **22 distinct `triaged_by` spellings**.

| Issue | Current `batch` | Required `batch` |
| --- | --- | --- |
| 4341 | `batch-014` | `batch-015` |
| 4350 | `batch-016` | `batch-015` |
| 4351 | `batch-012` | `batch-015` |
| 4384 | `batch-014` | `batch-015` |
| 4492 | `batch-016` | `batch-015` |
| 4501 | `batch-014` | `batch-015` |

| Issue | Current `triaged_by` | Dispatched model |
| --- | --- | --- |
| 4341 | `claude-opus-4.5` | `claude-opus-5` |
| 4350 | `GitHub Copilot CLI (Claude Sonnet 4.6)` | `claude-opus-5` |
| 4351 | `GitHub Copilot CLI (claude-opus-4.6)` | `claude-opus-5` |
| 4384 | `claude-opus-4.6 (Copilot CLI)` | `claude-opus-5` |
| 4415 | `claude-opus-4.5` | `claude-opus-5` |
| 4492 | `claude-sonnet-4.6` | `claude-opus-5` |
| 4501 | `GitHub Copilot CLI (claude-opus-4.6)` | `claude-opus-5` |

## Cross-issue decisions

### 4351 and 4273 — one rewriter reachability family, opposite failures

They are related, not duplicates. Both require `dxr.exe`, both exclude
v1.4.1907 because it lacks the rewriter option surface, and both expose
declaration-kind-specific reachability in `DoRewriteUnused`.

The outcomes point in opposite directions:

- 4273 retains too much: explicit `cbuffer` declarations are never removal
  candidates.
- 4351 removes too much: an array member's element type and an unread
  parameter's type are not marked live.

A fix should be reviewed as a reachability-policy change, not copied from one
issue to the other.

### 4415 and 4256 — validator trusts producer-owned state

These are distinct checks with the same validation boundary:

- 4256 shows that ViewID dependency state is never recomputed; later checking
  compares producer-derived representations.
- 4415 shows that `AnnotateHandle` is inspected for properties but skips the
  invalid handle operand, while the same operand on another opcode is rejected.

Together they show that DXIL validation does substantial structural checking
without independently verifying every producer-supplied semantic claim.
Neither issue is a duplicate of the other.

4415 does have a confirmed external duplicate: 6361 was closed with the
maintainer comment `Duplicate of #4415`.

### 4341 and 4350 — shared language-design context, different work

Both touch const instance methods and the implicit object parameter, but they
should not be merged:

- 4341 is a language capability gap: no reference return and no const-qualified
  overload pair can express a setter subscript.
- 4350 is invalid source accepted far enough to fail internally while lowering
  a write to a `$Globals`-backed object.

The first is an enhancement; the second is a compiler robustness defect even
if the wider language design remains open.

### 4350 and 4384 — both ICE-shaped, not one front-end defect

Both need build-independent `internal_failure` scoring and both are diagnosed
by the successor front end, but their paths are separate. 4350 fails in DXIL
lowering after Sema accepts a const violation; 4384 fails inside enum constant
conversion after the correct base-type diagnostic has already been buffered.

### Wider batch pattern

4307, 4350 and 4384 all show invalid source reaching a later generic failure or
internal failure instead of a source diagnostic. That is a routing pattern,
not a shared root cause. 4486 and 4497 are likewise both performance issues,
but one is an external SPIR-V loop-unroller limitation and the other is
whole-struct copy plus DXC `simplifycfg` behaviour.

## Independent draft review

All ten drafts were independently reviewed on `gpt-5.6-sol`, a different
model from the dispatched `claude-opus-5` authors. Concision was the primary
criterion; exact diagnostics, version ranges, symbols, file names, IR snippets
and stale-text findings were protected.

The initial write boundary allowed only this report and `reviewed_by`, which
blocked the draft edits. A follow-up explicitly authorised the ten batch-015
`comment.md` files. All listed corrections and cuts were then applied, and the
draft section below was re-rendered from those files.

| Issue | Review outcome |
| --- | --- |
| 4307 | Scoped `/Od` to the measured v1.9.2607 variant; removed the duplicated labels block and rhetorical generated-code sentence. Kept the stale-body warning and Debug assert. |
| 4341 | Added the missing partial-repro caveat: the assignment, profile and command are reconstructed. Trimmed introductory phrases; retained literal diagnostics, the mirror predicate and release floor. |
| 4350 | Replaced “exit status alone” with the precise status-set counterfactual and the syntax-error control result. Kept all four signatures. |
| 4351 | Removed the redundant build-identifier preamble and replaced “look like the same root cause” with the measured reachability facts. Kept the agent-constructed caveat for the second ask. |
| 4384 | Scoped the flag claim to the variants actually run and removed the redundant build-identifier footer. Kept the recovered literal diagnostics. |
| 4415 | Removed speculation about fix placement; retained the same-value/different-opcode control and preview-release caveat. |
| 4486 | Removed the counterfactual fix claim and added an explicit statement that the reported hardware timings, divergence and malioc results were not tested. |
| 4492 | Removed the unmeasured `int16_t`/`uint16_t` extension and prioritisation sentence. Kept the store result, shader-shape boundary and Clang layout caveat. |
| 4497 | Removed “bounded” effort language and the prediction that the same work must be repeated in the successor compiler. Kept the translated-pane caveat. |
| 4501 | Corrected “private tree” to fork-local; removed the unneeded hash-producer and milestone rhetoric. Kept the title/premise shift and instrument floor. |

I considered cutting four long caveats and rejected the cuts:

- 4307's `out`/`inout` distinction is the stale-text finding.
- 4415's two preview releases prevent an incidental validation error being
  misreported as a fixed→regressed transition.
- 4492's reporter-shader/minimal-shader split prevents a false regression date.
- 4501's older instruction-set floor prevents “not emitted” from being read as
  evidence from releases that could not express the request.

Those are actionable traps that have already produced wrong answers. Literal
diagnostic text was also left intact rather than paraphrased.

No required correction was dropped. Two optional cuts from the working review
were rejected on reflection:

- 4501 keeps the dated `-Fd` transition because it is the evidence that the
  title's premise changed after filing.
- 4486 keeps the `wont-fix`/`external` label caveat because it is an actionable
  maintainer decision, not an unsupported implementation claim.

Every verdict now records:

```text
gpt-5.6-sol (independent draft review, step 10)
```

The mandated `verdict --reviewed-by` command unexpectedly restamped
`triaged_at` as a second field. The original timestamps were restored, leaving
`reviewed_by` as the only persistent verdict change. That side effect should
be fixed before the command is relied on as a metadata-only merge.

## What this batch taught us about the method

### An idle worker is not a finished worker

Three of ten workers ended a turn immediately before the write-up. A targeted
follow-up recovered substantive results. Separately, 4497 produced 55
investigation artifacts but no `verdict.json`; its unambiguous, evidence-backed
notes allowed recovery.

The orchestrator should require both a substantive final response and a clean
per-issue `audit`. “The worker stopped” is not a completion signal, and
“captures exist but verdict is missing” is a mechanically detectable failure
state.

### Evidence boundaries must enumerate deliverable exceptions

The original collation boundary protected every issue directory while also
requiring edits to `comment.md` and `verdict.json`, which live inside those
directories. The boundary therefore overrode the deliverable twice: batch 014
recorded a real review without updating its artifacts, and batch 015 initially
did the same.

Default-deny remains right for captures and repro evidence, but the brief must
enumerate the allowed deliverables explicitly: the batch's `comment.md` files,
the `reviewed_by` field in its verdicts, and the batch report. A boundary that
names only protected directories cannot express that distinction.

### Provenance and batch identity belong to the orchestrator

Workers are unreliable witnesses to their own model identity, and this batch
also shows they are unreliable witnesses to batch membership when the brief
omits it. The orchestrator knows both values from dispatch and should stamp
them. Worker self-report produced seven wrong model identities here and six
wrong batch fields; the latter made the normal report renderer select only
four comments.

The existing corpus now has 22 spellings of `triaged_by`. Normalisation must
preserve real model differences between batches, but future values should not
be free-form worker input.

### The write boundary needs a negative form and a final filesystem check

A worker wrote `repro.hlsl` at the repository root as well as in its issue
directory. Two peers correctly refused to touch it, demonstrating the
single-owner rule, but the brief said where a worker may write without saying
explicitly that every other path is forbidden.

State both halves: write inside the assigned issue directory and nowhere else.
Before commit, check for new untracked files outside the skill tree. The stray
root file was absent at final collation.

### Live tooling changes must be additive and monotonic

Tooling changed while these workers were active: scoped path checking and
stricter text detection, optional diagnostic quotation sharing, and explicit
hypothesis metadata. The changes were benign because they were opt-in or
strictly tightened validation; old invocations retained their meaning.

The rule is not “never change tooling while batches overlap.” It is: do not
loosen, re-score or reinterpret an existing invocation under live workers.
Additive features and monotonic strictness can be safe when regression-tested.

### Measure inherited flags; do not inherit the previous conclusion

The same `-HV 2021` question resolved oppositely in adjacent batches. Removing
it recovered history for 4036; on 4341 it is load-bearing on four releases and
removing it would destroy valid probes.

Run with and without the inherited flag per release, especially for language
modes whose default changed. The transferable method is the comparison, not
“remove inherited flags.”

### Score candidate predicates against controls

4350's bare nonzero-exit candidate gets the probe's 20-release history exactly
right and is still wrong: it also fires on an ordinary diagnosed syntax error.
A candidate predicate is not validated by agreeing with the subject. Score it
against every discriminating control in the same counterfactual table.

4492 sharpens this further: each predicate needs a control capable of reaching
its positive anchor. A read-only shader is a vacuous control for a store
predicate even when it returns the desired `no-match`.

### A clean bisect boundary may only be a path-selection boundary

4492's reporter shader has a clean transition at v1.6.2104, but the minimal
construct reproduces on the oldest release. The older shader shape vectorises
the whole struct and never reaches the faulty per-element path.

Bisect answers when this input began producing this output. Before calling
that the defect's introduction, inspect the clean-side output, run a minimal
restatement, and see whether the control's lowering strategy changed at the
same boundary.

### Comparative issues need comparative history

4497 is “A is worse than B.” A one-sided bisect of A cannot establish whether
B was always better or improved later. Its 21-build `test1`/`test2` matrix is
the evidence for the historical asymmetry.

The same principle applies to mirror predicates: 4341 needed both “assignment
rejected” and “write landed” histories to exclude a silent-discard window.

### Absence claims need a positive instrument on every release

4307's release matrix requires the good diagnostic to fire somewhere;
4501 uses an anchor-only sibling predicate to ask whether each release can
emit and name the relevant instruction set. An absence without that positive
instrument is only a reader failure away from a false history.

The Compiler Explorer banner and embedded source are part of the instrument:
never put the token claimed absent into text that the compiler copies back
into its output.

### Validator acceptance needs mirrored controls and an engagement witness

4415 establishes the gap by holding the invalid handle value fixed and changing
only the opcode, then holding the instruction fixed and corrupting a different
operand. A generic garbage-module rejection would not isolate the missing
check.

When selecting an external signed validator, a version-mismatch witness proves
the environment variable actually selected it. Searching both release cache
roots also corrected the earlier false claim about when `dxv.exe` first
shipped.

### Arithmetic inside a predicate is another claim

4486 initially counted six control-flow-hint uses; the predicate failed its
declared positive expectation because the real count was five and the manual
count had included a metadata definition. Counts and universal quantifiers
need the same control discipline as the headline predicate.

### Cross-compiler success needs controls too

4492 proved Clang really used 16-bit types and compared only like-for-like
matrix layouts before saying its offsets were correct. A successful compile
can answer the wrong precision, layout or stage just as easily as a failed
compile can.

### Generators must fail before redaction can hide a bad input

One debugger generator computed a nonexistent compiler path. Path redaction
turned the wrong absolute path into a plausible `<repo>` path, making a failed
launch look like an empty stack result. Assert input paths exist before
running, assert text replacements matched and changed the source, and only
then redact generated output.

### Blind re-derivation should be standard for `close-fixed`

The orchestrator's two independent re-derivations of batch-014 fix
attributions matched the original workers and independently caught the
production-file commit arithmetic. No issue in this batch is `close-fixed`,
but the experiment shows that attribution can be tested rather than merely
reread at modest cost.

## Per-issue findings

### 4307 — Have a more explicit error when trying to use a struct member output interpolator as an input

The shipped behaviour is unchanged: a read-modify-write of
`_vertices[i].m_value` reaches the generic validator error on the entry-point
signature. Debug `main` asserts earlier in `LegalizeDxilInputOutputs`.

DXC already emits `error: output arrays of a mesh shader can not be read from`
at the offending line for `_vertices[i]` as a whole. The member expression
does not reach that existing Sema check. This is diagnostic work plus a real
Debug-assert robustness issue, not a missing understanding of the desired
message.

### 4341 — [HLSL 2021] Setter array subscript operator overload

Writing through a by-value `operator[]` is rejected with
`error: expression is not assignable` on all 16 HLSL-2021-capable releases.
The seeded-value and mirror-predicate design rules out a silent-discard window.

Reference returns remain unsupported, a trailing `const` cannot distinguish
the overload pair, and a named setter works. This remains a language
enhancement, not a DXC miscompile.

### 4350 — Internal Compiler error: calling method that modifies const object

All 20 stable releases fail internally, through four signatures. The front end
accepts a non-const method call that stores through a `$Globals`-backed object;
DXIL lowering then reaches a bad cast. The same invalid operation on a const
local compiles without a diagnostic, separating the missing const check from
the cbuffer-specific internal failure.

The successor front end diagnoses the const object directly. The issue should
remain open as a crash/incorrect-code handling defect even while the larger
const-instance-method design remains open.

### 4351 — Rewriter incorrectly removes types used in a member array

`dxr -remove-unused-globals` deletes `struct Child` while retaining
`Child MultipleChildren[2]`; compiling the rewritten source fails with
`unknown type name 'Child'`. The non-array member keeps the definition, and
the rewriter's own accounting changes from one type removed to zero.

The comment's unused-parameter case also reproduces with an explicitly
agent-constructed shader. The issue is live across all 19 releases with the
option surface and needs the `rewriter` routing label.

### 4384 — Integer vector as enum type causes ICE rather than error

All 20 stable releases fail internally, with three historical signatures.
Every build emits the correct `non-integral type 'uint3' is an invalid
underlying type` diagnostic for the scalar-enumerator control and compiles the
valid enum. Under the reported vector initializer, the correct diagnostic is
buffered and then lost when an HLSL-specific conversion kind reaches an
unhandled switch arm.

The title remains accurate. The current deterministic failure is only a
different face of the same defect.

### 4415 — Validator needs to prevent invalid handle in AnnotateHandle

The front end still emits only `-Wuninitialized` and succeeds. The validator
accepts `AnnotateHandle` with a zero or undefined handle in DXC output,
doctored modules and the signed shipping validator.

The same invalid handle on `textureLoad` is rejected with
`Instructions should not read uninitialized value.`, and corrupting the
properties operand of the same `AnnotateHandle` is rejected. The instruction
is inspected; its handle operand is the missing check.

### 4486 — SPIR-V nested `[unroll]` loops remain loops

All 19 SPIR-V-capable stable releases leave both loops with back-edges while
the thread's manual workaround is flat. Nesting alone is not the blocker: a
constant inner bound unrolls completely. The dependent inner bound prevents
the inner loop from being removed, so the outer loop never becomes eligible.

The same provably non-unrollable form is a hard diagnostic on the DXIL path and
is accepted with empty stderr and surviving loops on the SPIR-V path. Hardware
performance claims were not tested.

### 4492 — FP16 matrix element offsets are doubled

Structured-buffer matrix element loads use a four-byte step while the same
instruction records two-byte alignment. Sixteen loads span 62 bytes of a
32-byte element. Stores use the same wrong offsets; the final tested store
lands 28 bytes into the next element.

The reporter shader's v1.6.2104 boundary is only when its shape starts using
the faulty path. The minimal construct reproduces on every stable release.
Load and store controls remain correctly within 32 bytes, and the successor
compiler emits the correct like-for-like offsets.

### 4497 — struct value on "stack"

The by-value spelling copies the whole structured-buffer element before any
pass, making the float load unconditional; direct indexing leaves that load
inside the first branch. The exact asymmetry holds for both entry points on
all 21 measured builds.

Both outputs are valid and correct. This is a performance/code-quality
enhancement, not a correctness issue. The title is vague, but the emitted
`alloca` and whole-struct copy show why it was chosen.

### 4501 — SPIR-V split debug identifiers and storage paths

Neither requested instruction is emitted on any of the 16 stable releases
that can emit the relevant non-semantic debug instruction set. Older releases
are unmeasurable for this request, not clean negatives. Source and output both
support `never-implemented`.

Current DXC rejects `-Fd` with `-spirv`; the earliest relevant release instead
failed while trying to find a DXIL debug part. The open product question is
split SPIR-V debug information as a capability.

## Timeline integrity

Read-only timeline checks found zero cross-reference events on nine issues.
4415 has three pre-existing references, from 2024 and 2025, to 6971, 6361 and
293. All predate this batch. No cross-reference was created by the triage.

All ten issues were open in their captured `issue.json`; no GitHub mutation was
performed.

## Verification

- No `reindex` or bare `audit` was run while batch 016 workers were live.
- Before review stamping, all ten scoped audits reported only the expected
  missing `reviewed_by`; no evidence was missing.
- All ten verdicts now carry the required independent reviewer.
- The independent review edits were applied to all ten `comment.md` files.
- Release counts and history claims above were re-derived from capture headers
  and generated matrices.
- `python scripts\render_comments.py 015` was re-run. Its database query still
  selects only four issues because six verdicts have wrong batch metadata, so
  the same renderer code was then run against an in-memory, explicit ten-issue
  batch list. No database or verdict batch field was changed.
- The report path gate and all ten edited-issue path gates passed after the
  final render.
- GitHub access remained read-only.

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


### Draft — [#4307](https://github.com/microsoft/DirectXShaderCompiler/issues/4307) Have a more explicit error when trying to use a struct member output interpolator as an input

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4307](https://github.com/microsoft/DirectXShaderCompiler/issues/4307).

Still reproduces exactly as filed on `main` (`13730886e`), and on **every DXC release that has
ever had mesh shaders** — back to v1.5.2010 at `ms_6_5`, and all 18 releases from v1.6.2104 to
v1.9.2607 at `ms_6_6`. On v1.9.2607, dropping `/Od` leaves the same diagnostic.

```
$ dxc repro.hlsl /Zi /E main /Od /Fo test.mso /Tms_6_6 -Qembed_debug
error: validation errors

repro.hlsl:11: error: Function main with parameter is not permitted, it should be inlined.
Validation failed.
```

## DXC already has the diagnostic being asked for

Take the same shader and change line 22 to read the **whole element** instead of one member
(`case-elem-read.hlsl` below is `repro.hlsl` with only that line rewritten, keeping the line
numbering). DXC then produces exactly the shape of message the report asks for, on the line the
report asks for:

```
case-elem-read.hlsl:22:18: error: output arrays of a mesh shader can not be read from
                Vertex _copy = _vertices[ _sv_groupthreadid.x ]; _vertices[ 0 ].m_value = _copy.m_value * sign( toto );
                               ^
```

That is `err_hlsl_load_from_mesh_out_arrays`, emitted from `Sema::DefaultLvalueConversion`
([`SemaExpr.cpp:698`](https://github.com/microsoft/DirectXShaderCompiler/blob/main/tools/clang/lib/Sema/SemaExpr.cpp#L698)):

```cpp
if (isa<ArraySubscriptExpr>(E) && IsExprAccessingMeshOutArray(E)) {
  Diag(E->getExprLoc(), diag::err_hlsl_load_from_mesh_out_arrays);
```

`_vertices[i].m_value` is a `MemberExpr` whose base is the subscript, so `isa<ArraySubscriptExpr>`
is false — and `IsExprAccessingMeshOutArray` handles only `ArraySubscriptExpr`, `ImplicitCastExpr`
and `DeclRefExpr`, with no `MemberExpr` case either. The front end therefore says nothing
(`-fcgl` on the repro exits 0), the read-modify-write on the `out vertices` argument reaches
`LegalizeDxilInputOutputs`, whose `bLoad && bStore` switch has no case for the mesh qualifiers
and falls through without introducing a temporary, and the entry point arrives at the DXIL
validator still carrying a parameter — which is the generic message above, located on the
signature because a whole-module check has no idea about line 22.

So this looks like **extending an existing check to `arr[i].member`**, not adding a new
diagnostic. The diagnostic and its guard both arrived in `968fe4113` ("Add support for HLSL
Meshlets", 2019-07-11), which matches the release history: nothing regressed, the check was
simply never widened.

## Two other things the triage turned up

**A Debug build asserts on this shader**, before the reported message:
`DXASSERT(0, "invalid input qual here")` at `ScalarReplAggregatesHLSL.cpp:6065` in
`LegalizeDxilInputOutputs` — the `default:` arm of that same switch. Release builds compile the
assert out and fall through, which is why the shipped behaviour is a confusing validation error
rather than a diagnostic.

**The last paragraph of the report no longer describes DXC** (and may not have in 2022). Passing
the member to an `out float` parameter compiles **cleanly** on `main` and on all 18 releases;
passing the whole element to an `out Vertex` parameter produces the *good* diagnostic. Only
`inout` — which copies in as well as out, i.e. the same read as line 22 — reproduces the vague
error. Worth ignoring that sentence when scoping a fix.

[Compiler Explorer, dxc 1.6.2112 vs trunk](https://godbolt.org/z/Prfo6ssE7) — same message on
both. Note CE runs Release builds, so it cannot show the assert above; and `clang` there cannot
compile mesh shaders at all yet (`unknown type name 'vertices'`), so there is no successor
comparison to make.

The shader in the 2023 comment behaves identically — v1.9.2607 reports
`comment-repro.hlsl:166: error: Function main with parameter is not permitted, it should be
inlined.`, where line 166 is again the entry signature and the offending `inout` parameters are
at line 133.

**Labels:** keep `diagnostic`; suggest adding `enhancement` (the ask is a better error, not a
behaviour change), `incorrect-code` (this is about how invalid code is reported) and `crash`
(the measured assert above).

---

<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4341](https://github.com/microsoft/DirectXShaderCompiler/issues/4341) [HLSL 2021] Setter array subscript operator overload

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4341](https://github.com/microsoft/DirectXShaderCompiler/issues/4341).

Still reproduces: there is no way to write through a user-defined `operator[]` on
`main` (1.9.0.5433, `13730886e`) or on any release that supports HLSL 2021.

The issue supplies the getter but not the failing assignment, profile or command line. The
`m[0] = 9.0` harness below is reconstructed around that quoted struct, so repro quality is
partial.

The assignment is **rejected**, not silently dropped:

```
repro.hlsl:31:8: error: expression is not assignable
  m[0] = 9.0;
  ~~~~ ^
```

The repro seeds `A[0]` with `1.0`, runs `m[0] = 9.0;`, and returns `A[0]`, so a write that
landed and a write that was discarded would give different values. No release produces
either — the compile always fails, so this has been a diagnostic throughout rather than a
silent miscompile.

The two explanations in the thread still hold:

| | on `main` today |
| --- | --- |
| `float4 &operator[](int ix)` — the C++ setter spelling | `error: references are unsupported in HLSL` (`Sema::BuildReferenceType` rejects every reference type in HLSL, `tools/clang/lib/Sema/SemaType.cpp:1921-1925`) |
| a `const` getter beside a non-const setter | `error: class member cannot be redeclared` — the trailing `const` is not part of the signature, so the pair is a redeclaration, not an overload |
| a named `Set(int, float4)` method | works — the store lands, so mutating `A[]` from a member function is not the obstacle |

Reading through the same operator compiles cleanly, which is the control: the rejection is
specific to writing through it, not to `operator[]` or to HLSL 2021 support.

The diagnostic itself is not wrong — assigning to a prvalue is ill-formed in C++ too. What
is missing is a way to spell an overload that returns something assignable, so this is a
language gap rather than a DXC-side bug.

**Release history:** rejected identically on all 16 stable releases from v1.6.2112 (the first
release that accepts `-HV 2021`) through v1.9.2607. `-HV 2021` is required through
v1.7.2212.1 and inert from v1.7.2308, where the default moved. v1.4.1907, v1.5.2010,
v1.6.2104 and v1.6.2106 answer `Unknown HLSL version: 2021` for both the repro and a
feature-presence control, so they predate the language mode and are not evidence either way.

The Clang-based front end rejects this identically today.
[Compiler Explorer](https://godbolt.org/z/Y5d6e1r16) —
`hlsl_clang_trunk -fsyntax-only` emits the identical `expression is not assignable` at the
same column as both DXC panes, and the last pane compiles the same source with the assignment
removed (`-DCONTROL_NO_ASSIGN`) at exit 0, so the Clang result is not an artefact of
incomplete HLSL support.

Labels: this carries no kind label, so it does not show up in a feature-request search —
suggest adding `enhancement` and `hlsl2021` (the construct only exists under `-HV 2021`),
keeping `hlsl-next`. Whether the fix arrives as reference support, as
[const instance methods](https://github.com/microsoft/hlsl-specs/blob/main/proposals/0007-const-instance-methods.md),
or only in the Clang implementation is a language decision, not something this triage settles.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4350](https://github.com/microsoft/DirectXShaderCompiler/issues/4350) Internal Compiler error: calling method that modifies const object

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4350](https://github.com/microsoft/DirectXShaderCompiler/issues/4350).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on **every one of the 20 stable
releases** back to v1.4.1907 (2019-07), the oldest release tested that ships a usable `dxc`.
The repro is the issue body unchanged.

```
dxc -T vs_6_0 repro.hlsl
  -> error: llvm::cast<X>() argument of incompatible type!
  -> exit 0x80004005 (E_FAIL)
```

**Where it fails.** The front end accepts the write. Under `-fcgl`, which stops before DXIL
lowering, the compile succeeds and emits a store into the constant buffer (abridged — `!dbg`
metadata and mangled type suffixes elided):

```llvm
; in main
@"$Globals" = external constant %"$Globals"
%2 = call %"$Globals"* @"dx.hl.subscript.cb.rn…"(i32 6, %dx.types.Handle %1, i32 0)
%3 = getelementptr inbounds %"$Globals", %"$Globals"* %2, i32 0, i32 0
call void @"\01?Set@MyStruct@@QAAXXZ"(%struct.MyStruct* dereferenceable(4) %3)

; in Set
%Idx = getelementptr inbounds %struct.MyStruct, %struct.MyStruct* %this, i32 0, i32 0
store i32 1, i32* %Idx, align 4
```

Lowering then walks the users of that cbuffer address and hits
`cast<GetElementPtrInst>(user)` at `lib/HLSL/HLOperationLower.cpp:8847`, under the comment
`// Must be GEP here`:

```
llvm::cast<llvm::GetElementPtrInst,llvm::Instruction>
`anonymous namespace'::TranslateCBAddressUserLegacy
`anonymous namespace'::TranslateCBGepLegacy
`anonymous namespace'::TranslateCBAddressUserLegacy
`anonymous namespace'::TranslateCBOperationsLegacy
TranslateHLSubscript
```

**The const violation is never diagnosed, and that is separable from the crash.** The same
call on a `const` **local** object compiles to exit 0 with no diagnostic and no warning — a
local is an alloca, so the undiagnosed store is representable and lowering has nothing to
choke on. Making `Obj` `static` also compiles cleanly. The internal error needs the object to
be `$Globals`-backed; the missing check does not.

**The crash has four different signatures**, which matters for anyone re-testing this:

| releases | exit | stderr |
| --- | --- | --- |
| v1.4.1907, v1.5.2010 | `0xC0000005` | *empty* |
| v1.6.2104 | `0xC0000005` | `Internal compiler error: access violation…` |
| v1.6.2106, v1.6.2112 | `0x80AA001D` | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` |
| v1.7.2207 … v1.9.2607, `main` | `0x80004005` | `error: llvm::cast<X>() argument of incompatible type!` |

Matching on the message text reports a regression at v1.6.2106. Matching only the known
internal-failure status set, without text markers, reports it fixed at v1.7.2207. Bare
nonzero exit happens to classify all probe releases correctly, but it also fires on the
ordinary syntax-error control, which returns the same `0x80004005`. None is a valid account
of the history — the repro has failed internally on every release tested.

[Compiler Explorer, four panes](https://godbolt.org/z/TEcGjnve7). Both DXC panes fail
internally. `hlsl_clang_trunk` instead diagnoses it:

```
error: 'this' argument to member function 'Set' has type 'const MyStruct',
       but function is not marked const
note: 'Set' declared here
```

The fourth pane is the control for that: same compiler, same source, `-DCONTROL_MUTABLE` makes
the object `static`, and it compiles (exit 0). So this is a real diagnosis of the construct,
not Clang failing on the shader. This bears on the 2024-07-24 comment about overload resolution
not handling const-ness of the implicit object — the Clang-based front end does handle it
today. Whether that settles the design question in
[hlsl-specs 0007](https://github.com/microsoft/hlsl-specs/blob/main/proposals/0007-const-instance-methods.md)
is a language decision, not something this triage can answer.

**Labels**: suggest adding `crash` (every release fails internally, three with an access
violation, so `bug` alone understates it) and `incorrect-code` (the input is invalid HLSL and
its handling is the defect). `bug` and `hlsl-next` look right as they are.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4351](https://github.com/microsoft/DirectXShaderCompiler/issues/4351) Rewriter incorrectly removes types that are used in a member array of another struct

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4351](https://github.com/microsoft/DirectXShaderCompiler/issues/4351).

Still reproduces on `main` (1.9.0.5433, `13730886e`), using the command from the
report unchanged.

```
$ dxr -E InitArgs -remove-unused-globals repro.hlsl
struct Parent {
  Child MultipleChildren[2];
};
RWStructuredBuffer<Parent> ParentBuffer;
[numthreads(1, 1, 1)]
void InitArgs() {
  ParentBuffer[0] = (Parent)0;
}
```

The output does not compile:

```
$ dxc -T cs_6_0 -E InitArgs rewritten.hlsl
rewritten.hlsl:2:3: error: unknown type name 'Child'
```

`dxr -no-warnings` turns on the rewriter's accounting (the flag is inverted in
`dxr.cpp`), which shows the removal is deliberate rather than a printing bug —
`//found 1 types to remove` for the array form, `//found 0 types to remove` when
the same member is declared as plain `Child SingleChild;`. So the title's
attribution to the array is right: only the array form is affected.

The 2022-08-15 comment about unused function parameters also reproduces. That
comment had no repro, so this shader is mine — `Helper` takes two struct
parameters, one read and one not:

```
uint Helper(ParamUnused notRead, ParamUsed isRead) { return isRead.B; }
```

`struct ParamUsed` survives, `struct ParamUnused` is removed while the signature
that names it stays. Reading the parameter is what saves its type.

In `DoRewriteUnused` (`tools/clang/tools/libclang/dxcrewriteunused.cpp`), type
liveness is computed from *value references*. `SaveTypeDecl`'s field loop calls
`fieldDecl->getType()->getAsTagDecl()` (`:113`), which is null for a
`ConstantArrayType`, so an array member's element type is never marked used;
and nothing walks `FunctionDecl::params()` for type usage at all.

History: reproduces on every stable release that can express the option — 19 of
20, v1.5.2010 through v1.9.2607. v1.4.1907 is excluded rather than negative: its
`HLSLOptions.td` has no rewriter options, so the repro cannot be run there. Each
release was probed with the same `dxr.exe` loading that release's
`dxcompiler.dll`, with the non-array case as a per-release control.

Suggested label: **`rewriter`**, which is exactly what this is and currently
missing.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4384](https://github.com/microsoft/DirectXShaderCompiler/issues/4384) Integer vector as enum type causes ICE rather than error

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4384](https://github.com/microsoft/DirectXShaderCompiler/issues/4384).

Still reproduces on `main` (built at `13730886e`) and on all 20 stable releases from v1.4.1907
(2019-07) to v1.9.2607, so it predates the report rather than regressing into it. Confirmed on
DXIL as well as SPIR-V, per @llvm-beanz's note.

```hlsl
enum EE : uint3 {
    E = uint3(0,0,0),
};
[numthreads(1,1,1)] void main() {}
```

```
$ dxc -T cs_6_0 -E main repro.hlsl
Internal Compiler error: unknown conversion kind
UNREACHABLE executed at <build root>\tools\clang\lib\Sema\SemaOverload.cpp:5154!
```

(only the build root is elided above; everything else is verbatim.) The entry point is
incidental: the two-line snippet alone fails identically. The filed SPIR-V/`-O3`/`-Zpc`
flag set and explicit `-HV 2021` and `-HV 2018` variants also fail identically.

The crash presents differently across that history, which matters if anyone writes a test for
it: v1.4.1907 and v1.5.2010 access-violate with **empty stderr**, v1.6.2104 exits `0xE0000002`
with `LLVM Unreachable`, and v1.6.2106 onward exits `0x80AA001C` with the message above.
@Ipotrick's "reading illegal memory address, address varies from run to run" matches the oldest
two; current builds fail deterministically. Compiler Explorer's Linux Release builds `SIGSEGV`,
so this is not Debug-only — `llvm_unreachable` is `#if 1` in
`include/llvm/Support/ErrorHandling.h`.

**DXC already computes the error @pow2clk asked for, then throws it away.** Stepping over the
throw in a debugger shows what was in the diagnostic buffer at that moment:

```
repro.hlsl:1:11: error: non-integral type 'uint3' is an invalid underlying type
repro.hlsl:2:9: error: enumerator value is not a constant expression
```

The same shader with a scalar enumerator — `enum EE : uint3 { E = 0, };` — prints that first
error normally, on all 20 releases and on `main`. So the base-type check has been correct since
at least 2019; what is missing is only that an internal error discards every diagnostic
produced before it.

Root cause: `Sema::CheckEnumConstant` → `CheckConvertedConstantConversions`
(`SemaOverload.cpp:5101-5154`) switches over `SCS.Second`, and the five HLSL-specific
conversion kinds (`Overload.h:94-101`) are not listed, so they reach the closing
`llvm_unreachable("unknown conversion kind")`. Here `SCS.Second` is `ICK_HLSLVector_Truncation`
— `uint3(0,0,0)` truncated to the `int` the enum recovered to after `uint3` was rejected.

`hlsl_clang_trunk` already gets this right, with the same arguments:
`error: non-integral type 'uint3' (aka 'vector<uint, 3>') is an invalid underlying type`, plus
a `-Wconversion` warning on the enumerator, and no crash. Repro and both DXC panes:
https://godbolt.org/z/rMsGE4K4s

`tools/clang/test/SemaHLSL/enums.hlsl` already covers `half`, `float`, `double`, `min16float`
and `min10float` underlying types with that diagnostic, but has no vector case.

Label suggestions: add **`diagnostic`**, and consider removing **`hlsl2021`** — the crash is
language-version independent (identical at `-HV 2018` and `-HV 2021` on `main`, and present on
v1.4.1907, whose default predates HLSL 2021; DXC's own enum tests run at `-HV 2017`). The label
may reflect thread history not visible here.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4415](https://github.com/microsoft/DirectXShaderCompiler/issues/4415) Validator needs to prevent invalid handle in AnnotateHandle

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4415](https://github.com/microsoft/DirectXShaderCompiler/issues/4415).

Both asks still reproduce on `main` (1.9.0.5433, `13730886e`), unchanged since this was filed.

**The front-end half** is exactly as described: `-Wuninitialized` fires, the compile succeeds,
exit 0.

**The validator half** also holds, and the emitted instruction is still character-for-character
the one quoted above:

```
%1 = call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle zeroinitializer, %dx.types.ResourceProperties { i32 13, i32 4 })
```

Since the validator's job is to reject bad DXIL whatever produced it, this was also probed with
modules DXC never emitted — a valid module with the `annotateHandle` handle operand patched to
`zeroinitializer`, and again to `undef` — fed straight to `dxv`. Both: `Validation succeeded.`

The contrast that pins it down: **the same operand value on a different opcode is rejected by
name.**

```
$ dxv control-checkedop-zeroinit.ll
Function: main: error: Instructions should not read uninitialized value.
note: at '%3 = call %dx.types.ResRet.f32 @dx.op.textureLoad.f32(i32 66, %dx.types.Handle zeroinitializer, i32 0, i32 0, i32 0, i32 undef, i32 undef, i32 undef, i32 undef)' in block '#0' of function 'main'.
[3 further consequent errors elided]
Validation failed.
```

And corrupting the *props* operand of that very same `annotateHandle` call is rejected
(`Constant values must be in-range for operation.`), so the instruction is inspected — just
never its handle operand.

That matches the source. `ValidateHandleArgs()` in `lib/DxilValidation/DxilValidation.cpp`
routes `AnnotateHandle`, `AnnotateNodeHandle`, `AnnotateNodeRecordHandle` and
`CreateHandleForLib` to `break` under `// TODO: add custom validation for these intrinsics`;
every other opcode goes to `ValidateHandleArgsForInstruction()`, which raises
`InstrNoReadingUninitialized` for exactly this. That check landed in 9468120e6 (PR #5399,
2023-07-21) — after this issue — and excluded `AnnotateHandle` from the start.

**Not just this build**: pointing `dxv` at the signed `dxil.dll` from the v1.8.2505.1 release
archive (1.8.2505.32) gives the same split — the `textureLoad` module rejected, the
`annotateHandle` module accepted. Across releases, every one that can compile the repro
(v1.6.2112 through v1.9.2607) accepts it, and all six that ship `dxv.exe` accept the doctored
module too. The two SM 6.6 preview releases (v1.6.2104/2106) reject it, but only incidentally —
they lower `ResourceDescriptorHeap` to `createHandleForLib` and trip
`opcode 'CreateHandleForLib' should only be used in 'Library'`, not any handle rule.

<https://godbolt.org/z/156dMcvPv> — dxc 1.6.2112 and trunk, both emitting the instruction.

Labels `bug` + `validation` look right as they stand.
The front-end question — whether the warning should become an error by default — is a
product decision rather than a triage one.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4486](https://github.com/microsoft/DirectXShaderCompiler/issues/4486) [SPIR-V] Nested static 'for' loops with unroll translate to 'while( true )' loops with actual branches

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4486](https://github.com/microsoft/DirectXShaderCompiler/issues/4486).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on **every stable release that has a
SPIR-V backend** — all 19 from v1.5.2010 to v1.9.2607, with no clean release in between.
v1.4.1907, the oldest release here with a usable `dxc`, cannot answer at all: it exits 1 with
`dxc failed : SPIR-V CodeGen not available. Please recompile with -DENABLE_SPIRV_CODEGEN=ON.`,
on the trivial control as much as on the repro. So "always" means as far back as it is
possible to check, not back to the first release.

Compiler Explorer: <https://godbolt.org/z/dYWfKGE1o> (`-T ps_6_0 -E PS_bright_pass -spirv`,
with the DXIL output beside it).

```
               OpLoopMerge %114 %112 Unroll
               OpBranchConditional %113 %115 %114
...
               OpLoopMerge %122 %119 Unroll
               OpBranchConditional %121 %123 %122
```

Both `[unroll]` loops survive as real loops with back-edges; the `Unroll` loop control is
emitted and then not acted on. One `OpFOrdGreaterThan` remains where the unrolled nest would
have six. The workaround from the thread produces zero `OpLoopMerge` on the same builds, and
the sibling `[unroll] for (i < 4)` sampling loop in the same function *is* unrolled — so this
is not "`-spirv` ignores `[unroll]`".

s-perron's 2023-03-10 explanation holds up against the source
(`external/SPIRV-Tools/source/opt/loop_unroller.cpp:1113`, `// Can only unroll inner loops.`),
with one refinement worth recording: **nesting alone is not the blocker.** The same nest with
the inner bound changed from `4 - j - 1` to a constant unrolls completely — 0 `OpLoopMerge`, 9
comparisons, no branches. The failing ingredient is the inner trip count depending on the
outer induction variable: the inner loop's iteration count is not computable, so it is never
removed, so the outer never becomes inner-most either, and neither level is ever eligible.

A separate diagnostic gap appeared while checking pow2clk's DXIL claim, which is correct:
the repro fully unrolls to DXIL. Take the same nest with a uniform rather than literal outer
bound, so no `[unroll]` here can be honoured:

```
$ dxc -T ps_6_0 -E PS_bright_pass control-nonconst-nested.hlsl
control-nonconst-nested.hlsl:24:27: error: Could not unroll loop. Loop bound could not be deduced at compile time. Use [unroll(n)] to give an explicit count. Use '-HV 2016' to treat this as warning.

$ dxc -T ps_6_0 -E PS_bright_pass -spirv control-nonconst-nested.hlsl
[exit] 0                      # empty stderr, two surviving OpLoopMerge
```

An `[unroll]` that provably cannot be honoured is a hard error on one back end and silent on
the other.

This verifies compiler output only. I did not test the reported Mali/Adreno timing,
divergence or malioc results.

Suggested labels: **`performance`** (the generated SPIR-V retains runtime loops) and
**`up-for-grabs`** (recording the 2024-08-23 invitation, so someone looking for work can find
it). Whether `wont-fix` or `external` also apply is a call for a maintainer — the change would
land in SPIRV-Tools rather than in DXC's emitter.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4492](https://github.com/microsoft/DirectXShaderCompiler/issues/4492) [DXIL] Broken codegen for loading elements from FP16 matrix types in StructuredBuffer

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4492](https://github.com/microsoft/DirectXShaderCompiler/issues/4492).

Still reproduces on `main` (1.9.0.5433, `13730886e`). Your diagnosis is exactly right: the
element stride is 4 bytes where it should be 2.

Compiling your attached `1-mat.hlsl` unchanged:

```
;   struct struct.Test2_0
;   {
;       row_major half4x4 m_0;                        ; Offset:    0
;   } $Element;                                       ; Offset:    0 Size:    32

%7  = call %dx.types.ResRet.f16 @dx.op.rawBufferLoad.f16(i32 139, %dx.types.Handle %2, i32 0, i32 0, i8 1, i32 2)
%9  = call %dx.types.ResRet.f16 @dx.op.rawBufferLoad.f16(i32 139, %dx.types.Handle %2, i32 0, i32 4, i8 1, i32 2)
                                                        ... 8, 12, 16, ... 56 ...
%44 = call %dx.types.ResRet.f16 @dx.op.rawBufferLoad.f16(i32 139, %dx.types.Handle %2, i32 0, i32 60, i8 1, i32 2)
                                          ; RawBufferLoad(srv,index,elementOffset,mask,alignment)
```

Sixteen loads at `0, 4, … 60` — 62 bytes of a **32-byte** element, so the last eight read
past the end. `$Element` is correct, and each load's `alignment` operand is `2`, the real
size of `half`; the same instruction carries the right scalar size and steps by twice it.

The `define` body is byte-identical to the `.asm` you attached in 2022, on v1.6.2112,
v1.7.2207, v1.7.2212 and today's `main`.

**It is not a row/column-major mix-up.** For `a[0].xy` then `a[3].zw`, DXC emits `0, 4, 56,
60` row-major (correct `0, 2, 28, 30`) and `0, 16, 44, 60` column-major (correct `0, 8, 22,
30`) — each packing's correct sequence multiplied by two.

**Stores are affected the same way, and write out of bounds.** Writing `a[0][1]` and
`a[3][3]` through an `RWStructuredBuffer`:

```
call void @dx.op.rawBufferStore.f16(i32 140, %dx.types.Handle %1, i32 0, i32 4,  half 0xH3C00, ...)
call void @dx.op.rawBufferStore.f16(i32 140, %dx.types.Handle %1, i32 0, i32 60, half 0xH4000, ...)
```

Correct is 2 and 30; the second lands 28 bytes past the element, inside the next one. That
is a silent cross-element write.

**Source.** In `TranslateStructBufMatSubscript`
([`lib/HLSL/HLOperationLower.cpp#L9244`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/HLOperationLower.cpp#L9244))
the alignment is `DL.getTypeAllocSize(EltTy)` but the stride two lines later is
`GetEltTypeByteSizeForConstBuf(EltTy, DL)`, which returns 4 for anything ≤ 32 bits
("Constant buffer is 4 bytes align", with a `TODO: Use real size…`). That cbuffer rule is
being applied to a tightly-packed structured buffer. For 32-bit types the two agree. Only
`float16_t` was measured here.

**History.** A release scan puts your shader's first bad output at v1.6.2104, but that is a
shader-shape boundary, not the bug's: v1.4.1907 and v1.5.2010 load the whole 32-byte struct
up front as four `mask=15` loads and never reach the per-element path. Reduced to the
snippet in your issue body, it reproduces on **every** release back to v1.4.1907 — as far
back as I can check. `TranslateStructBufMatSubscript` dates to the repo's first commit.

**Clang gets it right.** In the linked panes `hlsl_clang_trunk` emits `0, 8, 22, 30` —
every offset inside the 32-byte element — where both DXC panes emit `0, 4, 56, 60`. Clang
models the member as `[4 x <4 x half>]` and strides by 2. One caveat when reading the link:
Clang lays the matrix out column-major regardless of `#pragma pack_matrix`, so those two
sequences are different layouts and only the *span* is directly comparable there. Compiling
the column-major variant locally makes it like-for-like — Clang `0, 8, 22, 30` against DXC
`0, 16, 44, 60`, exactly double again.

Compiler Explorer, three panes, on a minimal restatement of your snippet:
https://godbolt.org/z/3Pe367EfM

Labels look right as they are (`bug`, `matrix-bug`, `correctness`); not suggesting
`check-in-clang`, since that comparison is above.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4497](https://github.com/microsoft/DirectXShaderCompiler/issues/4497) struct value on "stack"

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4497](https://github.com/microsoft/DirectXShaderCompiler/issues/4497).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`), unchanged, and on **every** stable
release back to v1.4.1907 (2019). Compiler Explorer, annotated:
<https://godbolt.org/z/acfEvEz6o>

`-T ps_6_0 -E test1` — the `.f32` load is above the branch, and the two `[branch]` ifs are
folded into one:

```llvm
  %2 = call %dx.types.ResRet.f32 @dx.op.bufferLoad.f32(i32 68, %dx.types.Handle %1, i32 0, i32 0)
  %4 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 0, i32 12)
  %8 = and i1 %7, %6
  br i1 %8, label %9, label %10, !dx.controlflow.hints !10
```

`-E test2`, same file — the `.f32` load is inside the guarded block:

```llvm
  br i1 %4, label %5, label %10, !dx.controlflow.hints !10
; <label>:5
  %6 = call %dx.types.ResRet.f32 @dx.op.bufferLoad.f32(i32 68, %dx.types.Handle %1, i32 0, i32 0)
```

Both entry points were run on all 20 stable releases plus a Debug build of `main`: `test1`
hoists and `test2` does not, on all 21 builds. The asymmetry has never behaved differently, so
there is nothing to bisect and nothing in the report has gone stale.

**tex3d's 2022 analysis holds, and `-fcgl` shows it directly.** Before any pass runs, the front
end emits the whole-struct copy-in in the entry block:

```llvm
  %0 = alloca %struct.SData
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* %5, i8* %6, i64 32, i32 1, i1 false)
  call void @"\01?fct1@@YAXUSData@@@Z"(%struct.SData* %0)
```

Nothing hoists the load — it is unconditional from the first IR, and the optimizer only
narrows it (`value2` is dead, so what survives is `value.xyz` and `type`). A plain local
`SData data = dataBuffer[0];` with no function call behaves identically, so this is
whole-struct copy semantics rather than argument passing specifically.

The flattening is a consequence, not a second issue. DXC's `simplifycfg` does honour
`[branch]`, but only in two of the three flattening paths: `SpeculativelyExecuteBB`
(`SimplifyCFG.cpp:1494`) and `FoldTwoEntryPHINode` (`:1929`) both bail out on
`HasControlFlowHintToPreventFlatten`. The transform that actually fires here —
`FoldBranchToCommonDest` (`:2095`, which is what names the merged condition `%or.cond` at
`:2275`) — has no such guard. And it is legal here only *because* of the copy-in: it requires
everything ahead of the condition to be speculatable (`:2152`), which holds in `test1` where
the load is already in the entry block, and fails in `test2` where the load is inside the
guarded block. This matches the two follow-ups tex3d listed in 2022.

**The successor compiler reproduces the same asymmetry** (last two panes of the link,
`select i1 %5, i1 %8, i1 false` above a single branch for the by-value form). Those panes
compile a compute restating of the repro, because clang-dxc rejects `discard` today; the
restating was checked to still show the difference before it was published.

Label suggestion: keep `performance`, add `enhancement` — the input is valid, the output is
correct, and what is tracked here is two optimizer improvements rather than a defect. Not
suggesting `check-in-clang`, since the comparison above answers it.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

### Draft — [#4501](https://github.com/microsoft/DirectXShaderCompiler/issues/4501) [SPIR-V] Debug info should use DebugBuildIdentifier and DebugStoragePath with -Fd flag

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4501](https://github.com/microsoft/DirectXShaderCompiler/issues/4501).

Still open and still unimplemented on `main`
([13730886e](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e); the local
Debug build used here self-reports `1.9.0.5433` with a fork-local build identifier rather
than the public commit above).
Neither `DebugBuildIdentifier` nor `DebugStoragePath` is emitted in any mode, and `git grep`
finds no emitter, enumerator, test or doc for either anywhere in the tree.

In the richest mode DXC offers, `-fspv-debug=vulkan-with-source`, the module carries 16 kinds
of `NonSemantic.Shader.DebugInfo.100` instruction — including `DebugEntryPoint`, opcode **107**,
the immediate neighbour of the two requested ones. The gap is in what DXC emits, not in the
instruction set: 105 and 106 have been in SPIRV-Headers since 2021-03-24, and SPIRV-Tools
validates both (`source/val/validate_extensions.cpp`).

Measured on all 20 stable releases: 16 of them (v1.6.2112 2021-12 → v1.9.2607 2026-07) emit
`NonSemantic.Shader.DebugInfo.100` and none emits either instruction. The four older stable
releases cannot answer the question rather than answering it cleanly — v1.4.1907 has no SPIR-V
codegen, and v1.5.2010/v1.6.2104/v1.6.2106 predate `-fspv-debug=vulkan*` and emit
`OpenCL.DebugInfo.100`, whose opcodes stop at 36.

One thing has changed since 2022 and it changes the shape of the request. `-Fd` is now
rejected outright:

```
$ dxc -T ps_6_0 -E main -spirv -fspv-debug=vulkan-with-source -Fd spirv-pdb\ -Fo out.spv repro.hlsl
dxc failed : -Fd is not supported with -spirv
```

That explicit diagnostic was added on 2022-06-20, first shipped in v1.7.2207, 17 days after
this issue was filed. On v1.6.2112, current at filing, `-spirv -Fd` was accepted and then
failed with
`Unable to find required part in blob` — DXC looking for a DXIL debug part in a SPIR-V blob. So
there is no `-Fd` path for SPIR-V to extend: the ask is really "add split debug info to the
SPIR-V backend", with these two instructions as its module-side half.

Compiler Explorer, both panes emitting NonSemantic debug info and neither emitting the
requested instructions: <https://godbolt.org/z/cj44aEcbj>

Suggested labels: **`enhancement`** and **`debug info`**, alongside the existing `spirv`.
Nothing here is broken; this is a capability that was never built. Whether to build split
debug info for SPIR-V is a product decision, not something this triage can settle.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- No retroactive re-scoring occurred in this collation because `reindex` was
  deliberately withheld while batch 016 workers were live.
- The independent review was applied to all ten drafts. They remain unposted
  drafts requiring maintainer approval.
- Six incorrect `batch` fields and seven incorrect `triaged_by` values remain
  in the verdict artifacts because those metadata fields were not authorised
  for correction.
- 4256's older `dxv.exe` packaging count is contradicted by the unpacked,
  signed v1.8.2502 release and remains uncorrected in batch 014.
- 4486's hardware performance claims were not tested. 4341's failing
  assignment and 4351's function-parameter case are reconstructed from prose;
  4501's entire repro is agent-constructed. 4497's larger private shader was
  not available for byte comparison.
