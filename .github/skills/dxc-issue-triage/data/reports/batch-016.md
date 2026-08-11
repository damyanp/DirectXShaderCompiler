# DXC issue triage — batch 016

**Ground truth:** local Debug build `main-debug`, DXC `1.9.0.5433`, with
compiler source equivalent to public commit
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e).
The DLL self-reports
`1.10(5433-ab540090)(1.9.0.5433)`. All tracked changes after the public
commit are confined to the triage workspace, not DXC compiler source.

**Nothing was posted, edited, labelled, closed or reopened on GitHub. No DXC
compiler source was modified, and no commit or push was made.**

> [!IMPORTANT]
> **Sampling bias:** these ten issues are among the oldest open DXC issues.
> They are enriched for long-lived defects, dormant enhancements and issue
> text whose context has aged. Their verdict mix, subsystem mix and closure
> rate do not generalise to the backlog.

## Headline

- Nine issues still reproduce. 4527 is `changed-behavior`: the underlying
  defect remains, but stock DXC now rejects the shader instead of producing
  the object described by the issue.
- All ten verdicts are high confidence. None is recommended for closure.
  4615 and 4619 are enhancement requests; the other eight remain live
  compiler defects.
- Four descriptions are spot-check traps: 4520 quotes a specification sample
  removed in 2024; 4527 describes successful compilation that stock builds no
  longer permit; 4614 calls its attached repro a regression although every
  stable release fails; and 4619 combines a fixed reflection ask with one
  that remains open.
- The release scans agree on one 20-release stable set and use binaries from
  both release-cache roots. Feature-gated rows are reported as unmeasurable,
  not as clean results.
- Independent review found two substantive artifact overstatements and one
  predicate-semantics error. They do not change a verdict, but they are
  recorded below because the protected evidence files were not edited.

| Issue | Verdict / repro | History | Recommendation | CE |
| --- | --- | --- | --- | --- |
| [4514 — Variable inside a namespace not found](https://github.com/microsoft/DirectXShaderCompiler/issues/4514) | `repros` / complete | all 20 stable releases | keep open | [1497YdPj1](https://godbolt.org/z/1497YdPj1) |
| [4520 — heap sampler used inline in `Sample`](https://github.com/microsoft/DirectXShaderCompiler/issues/4520) | `repros` / complete | all 18 SM 6.6-capable stable releases | keep open | [dvYe69hdx](https://godbolt.org/z/dvYe69hdx) |
| [4527 — static const member-function array](https://github.com/microsoft/DirectXShaderCompiler/issues/4527) | `changed-behavior` / partial | exact attachment on 19 releases; restatement covers the oldest | keep open | [oYrbGzGq3](https://godbolt.org/z/oYrbGzGq3) |
| [4540 — static groupshared codegen](https://github.com/microsoft/DirectXShaderCompiler/issues/4540) | `repros` / complete | all 20 stable releases | keep open | [7Kexss5x8](https://godbolt.org/z/7Kexss5x8) |
| [4549 — acceleration structure on a UAV register](https://github.com/microsoft/DirectXShaderCompiler/issues/4549) | `repros` / complete | filed form on 18 releases; translated form covers all 20 | keep open | [5z1YfdTPE](https://godbolt.org/z/5z1YfdTPE) |
| [4605 — templated ROV byte-address load/store](https://github.com/microsoft/DirectXShaderCompiler/issues/4605) | `repros` / complete | all 20 stable releases | keep open | [nE7zvT4sx](https://godbolt.org/z/nE7zvT4sx) |
| [4614 — SROA empty-base assert/hang](https://github.com/microsoft/DirectXShaderCompiler/issues/4614) | `repros` / complete | all 20 stable releases | keep open | [erb45rxTb](https://godbolt.org/z/erb45rxTb) |
| [4615 — DXIL debug locations and `#line`](https://github.com/microsoft/DirectXShaderCompiler/issues/4615) | `repros` / agent-constructed | regressed in v1.5.2010 | enhancement; keep open | [fdMjWcKd1](https://godbolt.org/z/fdMjWcKd1) |
| [4619 — mesh reflection size/topology](https://github.com/microsoft/DirectXShaderCompiler/issues/4619) | `repros` / agent-constructed | topology absent on every mesh-capable release | enhancement; keep open | [oT63zTbMf](https://godbolt.org/z/oT63zTbMf) |
| [4629 — SROA interface/base-class failure](https://github.com/microsoft/DirectXShaderCompiler/issues/4629) | `repros` / complete | all 20 stable releases | keep open | [KcoeM9sra](https://godbolt.org/z/KcoeM9sra) |

## Text that no longer matches behaviour

> [!CAUTION]
> These are the highest-value findings in the batch. A reader who spot-checks
> only the issue text can reach the wrong “cannot reproduce” or “already
> fixed” conclusion.
>
> - **4520 — body premise:** the issue quotes a Dynamic Resources
>   specification example that used
>   `SamplerDescriptorHeap[sampIdx]` directly in `Sample`. DirectX-Specs
>   [PR #191](https://github.com/microsoft/DirectX-Specs/pull/191), merged
>   2024-09-04, replaced that example with a hoisted sampler. DXC still rejects
>   the inline form on every feature-capable release.
> - **4527 — body and title symptom:** “compiles successfully with no errors”
>   is not true of `main` or any measured stock release from v1.5.2010 onward.
>   They emit validation errors and no object, so the reported
>   `CreatePipelineState`-time failure is no longer the first visible failure.
>   `-Vd` can emit an unsigned container, but standalone validation rejects it.
> - **4614 — title:** “regression” is not supported for the attached repro.
>   Every stable release from v1.4.1907 onward fails. The reporter's production
>   shader was not attached, so this does not disprove a regression in that
>   unavailable input.
> - **4619 — title and first ask:** `GetThreadGroupSize` stopped returning
>   `0,0,0` for mesh shaders in v1.7.2212. The issue remains open only for
>   output primitive topology, but neither the title nor thread records that
>   split.

4615's “version >= 1.6” statement is also imprecise: the measured boundary is
v1.5.2010. It is not a `text_stale` finding because the statement did not
become false through later compiler movement; it was simply a coarse original
floor.

## Evidence verification and factual corrections

The standard history scans use the same 20 stable tags. Their catalog paths
visibly cover both physical roots:
`.cache\compilers\releases\` and
`build\tools\clang\test\dxc_releases\`. Neither root was treated as a
superset of the other.

The release outcomes were re-counted from captures and generated matrices:

- 4514: 20/20 reproduce; v1.4.1907 and `main` have byte-identical stderr.
- 4520: 18 reproductions and two honest feature-invalid rows.
- 4527: 19 primary reproductions and one feature-invalid row; the mesh-free
  restatement establishes the same validator failure on v1.4.1907.
- 4540: 20/20 reproduce; all 22 measured validators accept the bad `i1`
  module and reject the 64 KB groupshared control.
- 4549: 18 primary reproductions and two rows that do not measure the filed
  form; a `lib_6_3` translation establishes the register-class defect on both
  older releases.
- 4605: 20/20 reproduce, while templated `RWByteAddressBuffer` and untemplated
  ROV controls pass on every row.
- 4614: 20/20 releases fail; the assert-enabled build asserts and release
  builds hang.
- 4615: v1.4.1907 respects the virtual location; all 19 later releases use
  physical DXIL debug locations.
- 4619: the group-size ask changes at v1.7.2212; topology remains unavailable
  on all 19 mesh-capable releases and `main`.
- 4629: 20/20 fail; the oldest two spin and the later 18 fail internally.

### 4614 — predicate explanation contradicts the scoring implementation

`triage.py:is_internal_failure()` explicitly treats `timed_out` as an internal
failure. An independent read-only re-score with the bare
`{"kind":"internal_failure"}` predicate matched **21/21** primary captures,
including the 20 stable releases and `main`.

The explanation in 4614's `match.json`, generator, generated matrix, notes and
verdict summary says the opposite: that `internal_failure` scores a timeout
clean and that `any_of[timeout, internal_failure]` is required. The composed
predicate is harmless but redundant, so the 20/20 history and `repros`
verdict remain correct. The protected evidence files were not rewritten.

This is also a cross-issue inconsistency: 4629's method notes correctly state
that `internal_failure` includes timeouts. The tracked `triage.py` is
unmodified in this worktree, so the 4614 explanation is not supported by the
tool available to either worker or reviewer.

### 4549 — “unchanged” overstates the primary history

The verdict summary says the symptom reproduces “unchanged” through
v1.4.1907. The filed `ps_6_5`/`RayQuery` form is unavailable on v1.4.1907,
and v1.5.2010 access-violates rather than producing the later diagnostic. A
carefully translated `lib_6_3` case does establish the underlying
register-binding bug on both releases. The verdict is sound, but the primary
repro did not remain unchanged. The reviewed draft now distinguishes the two
histories.

### 4619 — topology history must be feature-scoped

The verdict summary's “all 20 releases” wording is too broad for the mesh
topology ask: v1.4.1907 cannot compile the mesh probe. The supported claim is
every **mesh-capable** stable release, 19 in total, plus `main`. The reviewed
draft uses that scope.

### Other corrections applied during review

- 4520 now says all **eight tested methods**, not every possible
  sampler-taking method.
- 4527 distinguishes the exact attachment's history from the mesh-free
  restatement and does not imply that the missing original command line was
  recovered.
- 4540 reports uniform validator outcomes without claiming that all 22 builds
  used identical diagnostic wording; current builds use a different literal
  overflow message.
- 4549 distinguishes a misleading diagnostic from the more serious measured
  fact that the `u` register class is dropped and the object is bound as
  `t0`.
- 4614 replaces “identical stacks” with the supported observation: samples
  stayed at the same depth in the same function.
- 4615 calls PR #2991 attribution “strongly supported,” not proven by a direct
  build of the fixing commit.

## Cross-issue decisions

### 4614 and 4629 — both SROA failures, distinct triggers

Both issues reach `ScalarReplAggregatesHLSL.cpp`, and both show why timeout
handling is part of internal-failure classification. They are not duplicates:

- 4614 is an empty-base/empty-member assignment that asserts in
  `SROA_Helper::RewriteBitCast` and otherwise leaves a use that is selected
  forever.
- 4629 combines a field-bearing base, a derived field and an interface; its
  later-release failure reaches a `cast<IntrinsicInst>`, while the oldest two
  releases spin.

The shared pass and failure shape justify reviewing fixes together, but the
controls isolate different source forms and different failing checks.

### 4527 and 4540 — “static” reaches different lowering defects

Both reports mention static storage, but the evidence separates them. 4527 is
a `linkonce_odr` static local whose `<3 x float>` element escapes
`LowerTypePass`; 4540 is an `internal` groupshared `uint` shrunk to `i1` by
`-globalopt`. They should not be merged merely because both involve globals.

### 4615 and 4619 — issue history can move without issue history events

Neither thread records the code change that determines its present scope.
Source/release history finds the v1.5.2010 `#line` behaviour boundary for 4615
and the v1.7.2212 mesh group-size fix for 4619. An empty issue timeline is not
evidence that compiler behaviour never moved.

## Independent draft review

All ten drafts were independently reviewed on `gpt-5.4`, a different model
from the dispatched `claude-opus-5` authors. Concision was the primary
criterion. Literal diagnostics, version boundaries, symbols, file names, IR
and actionable caveats were protected.

All ten comments were edited in place and then re-rendered. The resulting
drafts are 176–268 words each.

| Issue | Review edits and reason |
| --- | --- |
| 4514 | Reduced the draft to the exact diagnostic, 20-release history, lexical/semantic-parent evidence and bounded workaround controls. Removed repetition, rhetorical framing and unsupported effort implications; retained the inverse Clang lookup and no-label-change conclusion. |
| 4520 | Scoped the claim to the eight methods actually tested, removed broad rhetoric and fix-effort speculation, and retained the literal overload failure, feature floor, conversion controls and stale-specification warning. |
| 4527 | Led with the stale successful-compilation claim, separated the exact attachment from the v1.4 restatement, and retained the validation text and unrecoverable-command caveat. Removed speculative effort and claims broader than the measured configurations. |
| 4540 | Corrected the validator statement from uniform wording to uniform accept/reject outcomes. Kept the exact IR, DXIL rule, `-globalopt` isolation and untested-GPU caveat; cut redundant argument and root-cause rhetoric. |
| 4549 | Separated filed-form history from the `lib_6_3` translation, made the ignored register class explicit, and preserved both literal diagnostics and source symbols. Removed speculative effort/root-cause language and an unsupported `up-for-grabs` suggestion. |
| 4605 | Compressed the draft around the allow-list omission and three release-wide controls. Removed “cheap fix”/effort rhetoric while retaining the successor-front-end limitation and the maintainer-supported `up-for-grabs` suggestion. |
| 4614 | Put the stale “regression” title first, corrected “identical stacks” to the measured same-depth/same-function result, and removed the false claim that two predicate branches were independently necessary. Kept the #3016 distinction and the missing-production-shader caveat. |
| 4615 | Corrected the release floor to v1.5.2010 and softened definitive PR attribution to “strongly supported” because the exact commit was not built. Kept the diagnostic/SPIR-V contrast, option search and CE line-offset caveat. |
| 4619 | Split the two asks, marked the combined title/body stale, scoped topology to mesh-capable releases, and retained the `dxa -dumpreflection` instrument trap. Removed redundant narrative and recommended retitling to the remaining ask. |
| 4629 | Removed speculative root-cause and disposition rhetoric while preserving the literal Debug/Release failures, 18-crash/2-timeout history, discriminating inheritance control and `interface` language-design caveat. |

Every draft begins with the required warning and ends with:

```text
Triaged with AI assistance. Compiler output was produced by running the repro;
please flag anything that looks wrong.
```

Every verdict now records:

```text
batch:       batch-016
triaged_by:  claude-opus-5
reviewed_by: gpt-5.4
```

The original `triaged_at` timestamps were preserved. The nine stable
long-lived results use `always-repro'd`; 4615 uses
`regressed-in v1.5.2010`. No `history` field contains prose.

## What this batch taught us about the method

### Feature presence must be a per-release control

Diagnostic-shaped predicates can look positive when a release merely lacks
the profile, object kind or language feature. `classify` can demote a
`no-repro`, but it cannot rescue a false-positive `repro`. The SM 6.6 floor in
4520, mesh-free restatement in 4527 and translated profile in 4549 show the
needed pattern: prove the instrument first, then score the defect.

### A no-op-equivalent control validates nothing

4540's `-Oconfig` work found that a control whose expected output is also the
default/no-op output cannot prove that the requested pass pipeline ran.
Controls need a positive result that changes only when the instrument is
engaged.

### Split multi-ask and multi-phase reports before assigning one verdict

4527 separates compilation, container emission and runtime pipeline creation.
4619 separates group-size reflection from topology reflection. Scoring the
issue as one sentence would either hide a remaining defect or call a fixed
half still broken.

### Search source history even when the issue timeline is silent

4619 has no thread update for its group-size fix, yet release history and PR
#4745 identify it. 4615 likewise needs source ancestry to explain an
intentional historical behaviour change. Issue activity is not a substitute
for code history.

### A dumper that never calls the accessor is not a negative instrument

`dxa -dumpreflection` is silent about 4619's asks because it never calls
`GetThreadGroupSize` and only prints `GSOutputTopology` for geometry shaders.
Reflection dump silence therefore says nothing about whether the requested
mesh data is available.

### Absence predicates need invariant positive anchors

4615's metadata query checks both the missing virtual location and physical
file/line records that prove metadata parsing succeeded on that release.
Without a positive anchor, “not found” is indistinguishable from an
incompatible reader.

### Use the oldest sufficient flags, then prove equivalence

4520 needs `ps_6_6`; 4629 does not need the reporter's `-HV 2021` or newer
profile. Removing unnecessary flags can recover older history, but only after
controls show that the failing stack and source shape are unchanged.

### Literal diagnostic envelopes are not release-portable

4549's releases disagree on whether the same failure includes `error:` and on
whether it diagnoses or access-violates. Prefer semantic anchors or
non-diagnostic state, and preserve exact text only where the version scope is
known.

### Timeout metadata, not the displayed exit code, is authoritative

Timeout captures can contain `# exit: 0`. The `timed_out` header is the
measurement, and current `internal_failure` semantics intentionally include
it. 4614's contradictory explanation demonstrates why predicate semantics
should be stamped or tested in generated reports rather than restated by
hand.

### Search both release roots and trust catalog paths

Early DXC binaries often cannot self-report a usable identity. The release
catalog path is the attribution source, and both cache roots must be scanned.
The matrices in this batch agree because they consume those catalog paths
rather than assuming one root is complete.

### Preserve the review delta if exact auditability matters

The required workflow edits `comment.md` in place, and this batch had no
pre-review snapshots in version control. The table above records every
semantic edit, but a future reader cannot reconstruct the exact line-level
before/after wording. A future pass should retain a generated review diff or
commit worker drafts before collation without weakening the evidence boundary.

## Per-issue findings

### 4514 — Variable inside a namespace not found

All 20 releases reject qualified lookup with the same diagnostic. The
`cbuffer`/`tbuffer` declaration uses the translation unit as semantic parent
and the namespace only as lexical parent; transparent-buffer lookup exposes
the member unqualified but not as `testNamespace::testVariable`.

Unrelated preceding namespace declarations can perturb lookup, which explains
the reported texture workaround without making it a reliable fix. A second
buffer does not help, and moving the extra declaration after the use restores
the failure.

### 4520 — Sampler heap subscript used inline

All eight tested sampler-taking methods reject an inline
`SamplerDescriptorHeap` subscript on every SM 6.6-capable release. Hoisting,
explicit conversion and a user-defined sampler parameter prove that the
heap-to-object conversion exists; intrinsic argument matching lacks the
corresponding case.

The specification example was removed, not the compiler limitation. The issue
remains valid, but its quoted documentary premise is stale.

### 4527 — Static const array in a member function

Stock DXC now rejects the attachment with an unused external declaration and
an illegal `<3 x float>` validation path. The static local becomes a
`linkonce_odr` global, so the internal-linkage test skips type flattening.

The exact attachment is measurable from v1.5.2010; a mesh-free restatement
shows the same defect on v1.4.1907. The original command that reportedly
produced an object was not recorded, so only the underlying compiler defect,
not that historical configuration, is reproducible.

### 4540 — Static groupshared `uint` becomes `i1`

`-globalopt` alone shrinks the internal groupshared global from `i32` to `i1`,
although DXIL permits `i1` only for thread-local memory. The full pipeline does
the same; removing `-globalopt` preserves `i32`.

Every measured validator accepts the bad module while rejecting the
groupshared-overflow control. The issue remains both a code-generation and a
validation defect. Reported GPU behaviour was not tested.

### 4549 — Acceleration structure declared on a UAV register

DXC drops the `u` class, preserves the number and binds the acceleration
structure as `t0`. An overlap diagnostic appears only when another resource
occupies that slot, so this is incorrect binding as well as a misleading
message.

The filed RayQuery form covers 18 releases; a profile-compatible translation
shows the same missing register-class check on the two oldest. The existing
front end already emits the useful “expected `t` binding” diagnostic for
another SRV-class object.

### 4605 — Templated ROV byte-address load/store

All 20 releases reject explicit template arguments on
`RasterizerOrderedByteAddressBuffer::Load` and `Store`. The explicit-template
allow-list names the ordinary read-only and read/write byte-address types but
omits the ROV type.

Templated operations on `RWByteAddressBuffer` and untemplated ROV loads pass
throughout history, ruling out a feature-floor explanation. The successor
front end's broader inability to load from the ROV type is separate.

### 4614 — Empty-base SROA assert/hang

The assert-enabled build stops on a type mismatch. With assertions removed,
the uneliminated bitcast use is selected repeatedly and release builds hang.
All 20 stable releases fail, including the first release containing the fix
for #3016.

That older fix covers an empty first member, not this base-class plus
empty-member assignment. Making the base non-empty, removing the assignment or
using composition avoids the failure. The attached repro is not a regression;
the unavailable production shader may have had a different boundary.

### 4615 — DXIL debug locations ignore `#line`

v1.4.1907 emits the virtual file and line. From v1.5.2010 onward, DXIL debug
locations use physical source positions. PR #2991 changed the relevant calls
to `UseLineDirectives=false` and added a test for that behaviour.

Diagnostics and SPIR-V line records still honor the directive, and the
successor front end already emits the virtual DXIL location. No DXIL opt-in
exists, so the remaining request is an enhancement rather than a regression
bug.

### 4619 — Mesh reflection has one fixed ask and one open ask

`GetThreadGroupSize` returns `0,0,0` through v1.7.2207 and the correct
`32,2,1` from v1.7.2212 onward. Release ancestry identifies PR #4745 as that
unrecorded fix.

Output primitive topology remains absent from the public shader-reflection
surface on every mesh-capable release and `main`, although the container and
mesh-state metadata carry `Triangle`. Retitling the issue to the remaining
topology request would prevent the fixed half from obscuring it.

### 4629 — Interface/base-class SROA failure

Debug `main` asserts that a struct bitcast should have only lifetime-marker
uses; release `main` reaches an incompatible `cast<IntrinsicInst>`. Eighteen
stable releases fail internally, while v1.4.1907 and v1.5.2010 spin for the
full timeout with one core busy.

The discriminating source shape is a field-bearing base, another field in the
derived class and an implemented interface. Removing the interface compiles on
every release. A proposal to remove HLSL `interface` makes final disposition a
language decision, but the current compiler failure remains a live defect.

## Timeline integrity

Read-only timeline checks found pre-existing cross-references only:

- 4514 has three, the latest dated 2025-04-29.
- 4520 references DirectX-Specs PR #191.
- 4615 references issue #8679.
- 4629 has two.
- 4527, 4540, 4549, 4605, 4614 and 4619 have none.

No event was created by this triage. All ten captured issues are open, and no
GitHub mutation was performed.

## Reconstruction gaps

- 4520's issue directory contains the conclusion about DirectX-Specs #191 but
  not a captured API response or patch. This collation independently verified
  by read-only GitHub API that the PR titled “Remove nonworking code from
  Dynamic Resources spec” merged on 2024-09-04 and replaced the inline sample.
- 4614's artifacts do not stamp the scoring-tool revision. They therefore
  cannot explain their own contradiction with `is_internal_failure`; the
  repository state and an independent re-score establish that the written
  predicate explanation is wrong.
- Exact pre-review draft wording is gone because `comment.md` is an in-place
  deliverable and no worker-draft snapshot was committed. The independent
  review table preserves the substantive changes, not a line-level diff.
- 4527 omits the reporter's original command line; the configuration that
  emitted the reported container cannot be reconstructed.
- 4614 omits the production shader behind the reporter's regression
  impression. Only the attached reduced repro was measured.
- 4540's GPU result was not measured. 4615 and 4619 necessarily use
  agent-constructed API harnesses because neither issue supplies a complete
  executable repro.

These limits do not change the recorded verdicts. They bound what the evidence
can support.

## Verification

- `python scripts\triage.py audit --issue <n>` passed independently for all
  ten issues: each reported `no missing evidence in 1 issue(s)`.
- `python scripts\check_paths.py` passed: 5,442 committable text files,
  16 allowlisted matches in four files, and no unexpected machine paths.
- `python scripts\render_comments.py 016` selected and spliced all ten
  reviewed drafts.
- All ten verdicts have the required batch, author, reviewer and short
  taxonomy history values.
- All ten rendered drafts have the required warning and AI-assistance trailer.
- `SKILL.md`, `triage.py`, DXC source and captured evidence were not modified.
- GitHub access remained read-only. Neither `reindex` nor
  `scripts\render_overview.py` was run.

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


### Draft — [#4514](https://github.com/microsoft/DirectXShaderCompiler/issues/4514) Variable inside a namespace not found

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4514](https://github.com/microsoft/DirectXShaderCompiler/issues/4514).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on all 20 stable
releases from v1.4.1907 to v1.9.2607:

```
repro.hlsl:15:9: error: no member named 'testVariable' in namespace 'testNamespace'; did you mean simply 'testVariable'?
    if( testNamespace::testVariable * tid.x > 0 )
        ^~~~~~~~~~~~~~~~~~~~~~~~~~~
        testVariable
```

The result is unchanged under `-HV 2016`, `2017`, `2018` and `2021`.

Source and controls point to the declaration context. `HLSLBufferDecl::Create`
uses the translation unit as the semantic parent for `cbuffer`/`tbuffer`
(`SemaHLSL.cpp:15420`), while the namespace is only the lexical parent.
Because `HLSLBufferDecl` is transparent (`DeclBase.cpp:913`), the member is
visible unqualified from the translation unit but is missing from qualified
namespace lookup.

The reported `Texture2D` workaround is incidental: a preceding namespace-scope
`static uint` or `struct` also makes lookup succeed. A second `cbuffer` does
not, and moving the extra declaration below `main` makes the error return.
`tbuffer` is affected too.

[Compiler Explorer](https://godbolt.org/z/1497YdPj1) shows DXC 1.6.2112,
trunk, and the workaround. The two Clang panes show the inverse lookup:
`testNamespace::testVariable` is accepted and the unqualified spelling is
rejected.

The existing `bug` label still fits; no label change is suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4520](https://github.com/microsoft/DirectXShaderCompiler/issues/4520) SamplerDescriptorHeap[sampIdx] cannot be used inside of texture.Sample(...)

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4520](https://github.com/microsoft/DirectXShaderCompiler/issues/4520).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on all 18 stable
releases with SM 6.6 dynamic resources, v1.6.2104 through v1.9.2607.
v1.4.1907 and v1.5.2010 reject `ps_6_6`, so they are not evidence.

```
repro.hlsl:4:31: error: no matching member function for call to 'Sample'
    float4 result = myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
                    ~~~~~~~~~~^~~~~~
repro.hlsl:4:31: note: candidate function template not viable: requires 3 arguments, but 2 were provided
```

All eight tested sampler-taking methods reject an inline heap subscript and
compile when it is hoisted into a local: `Sample`, `SampleLevel`,
`SampleBias`, `SampleGrad`, `SampleCmp`, `SampleCmpLevelZero`, `GatherRed`
and `CalculateLevelOfDetail`. The comparison-state cases used
`SamplerComparisonState`, so this is not a sampler-kind mix-up.

The conversion exists: initialization, an explicit cast and a user-defined
`SamplerState` parameter all compile on every feature-capable build.
`CanConvert` has the heap-to-object case (`SemaHLSL.cpp:10353`), while
intrinsic argument matching reaches `CombineObjectTypes`
(`SemaHLSL.cpp:7354`), which has no heap-sampler case. The intended candidate
is dropped, leaving the generic overload error and arity notes.

The issue body's quoted specification sample is now stale:
[DirectX-Specs#191](https://github.com/microsoft/DirectX-Specs/pull/191)
removed it in 2024. The compiler behaviour did not change. The Clang-based
front end still cannot test this case because it rejects
`ResourceDescriptorHeap` and the workaround as undeclared.

Compiler Explorer: <https://godbolt.org/z/dvYe69hdx>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4527](https://github.com/microsoft/DirectXShaderCompiler/issues/4527) Using a static const array in a member function declaration causes CREATEPIXELSHADER_INVALIDSHADERBYTECODE during CreatePipelineState

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4527](https://github.com/microsoft/DirectXShaderCompiler/issues/4527).

The underlying defect is still present, but the issue body's statement that
the shader “compiles successfully with no errors” no longer matches stock DXC
behaviour. `main` (1.9.0.5433, `13730886e`) rejects the attached file and
writes no object:

```
error: validation errors

error: External declaration '\01?kValues@?1??GetTestValue@MyClass@@QAA?AV?$vector@M$02@@I@Z@4QBV3@B' is unused.
error: Vector type '<3 x float>' is not allowed.
repro.hlsl:93:16: error: Instructions must be of an allowed type.
note: at '%6 = extractelement <3 x float> %5, i64 0' in block '#0' of function 'mainPS'.
Validation failed.
```

The attachment reproduces from v1.5.2010 through v1.9.2607. v1.4.1907 cannot
parse its unused mesh entry point, but a mesh-free restatement produces the
same validation failure there. The pixel and mesh entry points fail alike,
and all three workarounds in the report still compile.

The static local is serialized as a `linkonce_odr` global:

```llvm
@"\01?kValues@..." = linkonce_odr constant [3 x <3 x float>] ...
```

`dxilutil::IsStaticGlobal()` requires `InternalLinkage`
(`lib/DXIL/DxilUtil.cpp:114`), so `LowerTypePass` skips this global and never
flattens the `<3 x float>` element type. The global-scope control instead
reaches the container as `internal constant [9 x float]`.

`-Vd` is the only tested configuration that emits a container; it is unsigned
and standalone `dxv` rejects its DXIL. The issue does not record the original
command line, so the configuration that produced the reported object cannot
be recovered.

Compiler Explorer: <https://godbolt.org/z/oYrbGzGq3>. Suggested label: `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4540](https://github.com/microsoft/DirectXShaderCompiler/issues/4540) [DXIL] Incorrect codegen when using "static" on groupshared variables

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4540](https://github.com/microsoft/DirectXShaderCompiler/issues/4540).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on all 20 stable
releases from v1.4.1907 to v1.9.2607.

```llvm
; static groupshared uint storeTile;
@storeTile = internal unnamed_addr addrspace(3) global i1 false
  store i1 false, i1 addrspace(3)* @storeTile, align 4

; groupshared uint storeTile;
@"\01?storeTile@@3IA" = external addrspace(3) global i32, align 4
  store i32 0, i32 addrspace(3)* @"\01?storeTile@@3IA", align 4, !tbaa !12
```

`docs/DXIL.rst` defines `i32`, `f32` and `f64` memory accesses for
groupshared memory; `i1` is listed only for thread-local memory.

The validator/spec contradiction is also reproducible. Across 22 builds
(20 stable releases, v1.5.2003 and `main`), validation accepts the `i1`
groupshared module on 22/22. A 64 KB groupshared control is rejected on 22/22;
current `main` reports:

```
control-tgsm-overflow.hlsl:13:2: error: Total Thread Group Shared Memory used by 'main' is 65536, exceeding maximum: 32768.
```

`dxopt` measurements isolate the change to `-globalopt`: the front-end module
and a no-pass control contain `i32`; `-globalopt` alone and the full pipeline
produce `i1`; removing `-globalopt` from the full pipeline preserves `i32`.
This matches `TryToShrinkGlobalToBoolean`
(`lib/Transforms/IPO/GlobalOpt.cpp:1595`).

Compiler Explorer: <https://godbolt.org/z/7Kexss5x8>. The reported GPU
behaviour was not tested here. The existing `bug`, `correctness` and
`validation` labels remain appropriate.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4549](https://github.com/microsoft/DirectXShaderCompiler/issues/4549) [HLSL] Misleading error message when using a UAV register for a raytracing acceleration structure

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4549](https://github.com/microsoft/DirectXShaderCompiler/issues/4549).

Still reproduces on `main` (1.9.0.5433, `13730886e`). The filed
`ps_6_5`/`RayQuery` form is measurable from v1.6.2104; a `lib_6_3`
restatement shows the same register-class bug back to v1.4.1907.

The `u` is not merely omitted from the diagnostic; it is ignored in the
binding. With the acceleration structure at `register(u0)` and nothing at
`t0`, DXC compiles without a diagnostic and emits:

```
; opaque_as                         texture     i32         ras      T0             t0     1
```

The reported overlap appears only when that `t0` is occupied. With `-Zi`, the
caret points at the correctly declared resource:

```
repro.hlsl:13:1: error: resource depth_buffer at register 0 overlaps with resource opaque_as at register 0, space 0
Texture2D<float> depth_buffer : register(t0);
^
```

`hlsl::DiagnoseRegisterType` has no
`AR_OBJECT_ACCELERATION_STRUCT` case (`SemaHLSL.cpp:11866`), so the invalid
register class is not diagnosed. `InitFromUnusualAnnotations`
(`CGHLSLMS.cpp:3172`) keeps the number but drops the letter; allocation later
sees two SRVs at `t0`.

DXC already emits the useful diagnostic for another SRV-class resource:

```
error: invalid register specification, expected 't' binding
```

Compiler Explorer: <https://godbolt.org/z/5z1YfdTPE>. Suggested labels:
add `bug` and `incorrect-code`; keep `diagnostic`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4605](https://github.com/microsoft/DirectXShaderCompiler/issues/4605) RasterizerOrderedByteAddressBuffer doesn't accept templated Load/Store

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4605](https://github.com/microsoft/DirectXShaderCompiler/issues/4605).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on all 20 stable
releases from v1.4.1907 to v1.9.2607:

```
repro.hlsl:4:18: error: Explicit template arguments on intrinsic Load are not supported
  return buf.Load<float4>(idx1);
                 ^
```

`Store<float4>` gets the corresponding `Store` diagnostic. The same templated
operations compile on `RWByteAddressBuffer`, and untemplated `Load` compiles
on `RasterizerOrderedByteAddressBuffer`. Those controls pass on every release,
so none of the 20 predates templated byte-address `Load<T>`/`Store<T>`.

The rejection comes from the explicit-template-argument allow-list in
`tools/clang/lib/Sema/SemaHLSL.cpp:11379`: it names
`ByteAddressBuffer` and `RWByteAddressBuffer`, but not
`RasterizerOrderedByteAddressBuffer`. No current test covers the templated ROV
forms.

[Compiler Explorer](https://godbolt.org/z/nE7zvT4sx) also shows that the
Clang-based front end rejects `Load` on the ROV type with or without template
arguments, so that is a wider implementation gap rather than this exact
defect.

Suggested label: add `up-for-grabs`, matching the maintainer comment that PRs
are welcome although a proactive DXC fix is not planned.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4614](https://github.com/microsoft/DirectXShaderCompiler/issues/4614) Assert/hang in SROA_HLSL pass related to empty base struct regression

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4614](https://github.com/microsoft/DirectXShaderCompiler/issues/4614).

Still reproduces on `main` (1.9.0.5433, `13730886e`), but the title's
“regression” does not match the release history of the attached repro: all 20
stable releases from v1.4.1907 to v1.9.2607 fail.

The assert-enabled build stops in `SROA_Helper::RewriteBitCast`:

```
Error: assert(0 && "Type mismatch.")
File:
lib\Transforms\Scalar\ScalarReplAggregatesHLSL.cpp(2690)
```

Release builds hang instead. Continuing past the assert reaches DXC's own
progress check:

```
Infinite loop while SROA'ing value, use isn't getting eliminated.
```

The source connects the two signatures. The assert is followed by `return`, so
with `NDEBUG` the bitcast use remains; the loop in `RewriteForScalarRepl`
re-selects it, while its `DXASSERT_LOCALVAR` guard is compiled out. A
v1.9.2607 run remained active for 300 seconds, and stack samples 60 seconds
apart stayed at the same depth in the same function.

v1.6.2106, the first release containing `527d58e5a` (“Fixes #3016”), also
hangs. That change and its regression test cover an empty first member, not
the base-class plus empty-member assignment in this repro. The added test
still compiles; this shader does not. Variants that make the base non-empty,
remove the assignment, or replace inheritance with composition compile.

Compiler Explorer: <https://godbolt.org/z/erb45rxTb>. This history applies to
the attached repro; it cannot determine whether the reporter met a new
occurrence in a different production shader.

Suggested labels: add `type-system` and `test`; keep `crash`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4615](https://github.com/microsoft/DirectXShaderCompiler/issues/4615) DXIL debug locations do not respect #line directives

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4615](https://github.com/microsoft/DirectXShaderCompiler/issues/4615).

Still current on `main` (1.9.0.5433, `13730886e`). With one statement before
and one after `#line 400 "virtual-source.hlsl"`, DXIL debug metadata keeps the
physical file and lines:

```llvm
!1  = !DIFile(filename: "repro.hlsl", directory: "")
!68 = !DILocation(line: 7, column: 10, scope: !4)
!69 = !DILocation(line: 9, column: 17, scope: !4)
```

The measured boundary is v1.5.2010, not version 1.6: v1.4.1907 emits
`!DILocation(line: 400)` and `!DIFile(filename: "virtual-source.hlsl")`;
all 19 later stable releases use physical locations.

The boundary and source history strongly support the issue's attribution to
PR #2991 (`bce85df11`). That commit lies between those two releases, changed
the `getPresumedLoc` calls to pass `UseLineDirectives=false`, and added
`pound_line.hlsl`, which tests the current behaviour.

The compiler still treats other consumers differently. A diagnostic after the
directive reports:

```
virtual-source.hlsl:400:17: error: invalid format for vector swizzle 'no_such_member'
```

and `-spirv -fspv-debug=line` emits `OpLine` for virtual line 400. No opt-in
flag exists for DXIL debug locations. `-ignore-line-directives` goes the other
way, making diagnostics physical too; `-line-directive` is rewriter-only.

[Compiler Explorer](https://godbolt.org/z/fdMjWcKd1) shows the DXIL/SPIR-V
contrast and that `hlsl_clang_trunk` already emits the virtual location. CE's
banner shifts physical lines 7 and 9 to 31 and 33; that is not a compiler
difference.

Suggested labels: `debug info` and `enhancement`. The remaining request is an
opt-in flag, so `enhancement-not-bug` remains the recommended disposition.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4619](https://github.com/microsoft/DirectXShaderCompiler/issues/4619) How to get thread group size and output primitive topology in MeshShader?

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4619](https://github.com/microsoft/DirectXShaderCompiler/issues/4619).

The issue has two asks with different answers. Its body and title are now
stale because the thread-group-size half was fixed, while the topology half
remains open.

## Thread group size

`ID3D12ShaderReflection::GetThreadGroupSize` returned `0,0,0` for mesh
shaders through v1.7.2207. The measured transition is:

| release | `[numthreads(32,2,1)]` result |
| --- | --- |
| v1.5.2010 … v1.7.2207 | `0,0,0` |
| v1.7.2212 and later | `32,2,1` |

The release boundary and source change identify PR #4745
(`80fb4622a`, merged 2022-10-27) as the fix. It changed the reflection guard
from compute-only to compute, mesh and amplification shaders, but did not
reference this issue. The issue still has no comments recording that result.

## Output primitive topology

This remains unavailable through `ID3D12ShaderReflection`. On every
mesh-capable release and on `main`, the topology-shaped
`D3D12_SHADER_DESC` fields are zero. The container does carry the data:
`PSVRuntimeInfo1::MS1.MeshOutputTopology` is `2` (`Triangle`), and the DXIL
mesh-state metadata includes the same value.

[Compiler Explorer](https://godbolt.org/z/oT63zTbMf) shows the mesh-state
metadata for `[outputtopology("triangle")]` and `[numthreads(32,2,1)]`:

```llvm
!61 = !{i32 9, !62}
!62 = !{!63, i32 3, i32 1, i32 2, i32 0}
!63 = !{i32 32, i32 2, i32 1}
```

`dxa -dumpreflection` cannot verify either ask: it never calls
`GetThreadGroupSize` and prints `GSOutputTopology` only for geometry shaders.

Retitling this issue to the topology request and noting #4745 would describe
the remaining work. Exposing topology needs reflection API surface, so the
existing `enhancement` and `reflection` labels remain appropriate.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4629](https://github.com/microsoft/DirectXShaderCompiler/issues/4629) Internal llvm::cast<X> due to particular combination of class fields and methods

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4629](https://github.com/microsoft/DirectXShaderCompiler/issues/4629).

Still reproduces on `main` (1.9.0.5433, `13730886e`). The filed command also
reproduces; the release-history scan used `ps_6_0` without `-HV 2021` after
controls showed those flags do not change the failing stack.

The Debug build stops at:

```
Assertion failed: !(onlyUsedByLifetimeMarkers(BCI))
  "expected struct bitcast to only be used by lifetime intrinsics"
  lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp(2630)
```

Under `NDEBUG`, that check disappears and the same value reaches the
`cast<IntrinsicInst>` two lines later:

```
error: llvm::cast<X>() argument of incompatible type!
```

All 20 stable releases fail on this shader. Eighteen fail internally: 17 emit
the reported cast message and v1.6.2104 access-violates. The two oldest,
v1.4.1907 and v1.5.2010, instead run for 240 seconds with no output while
using one full CPU core; a trivial shader compiles on both in 0.3 seconds.

The trigger is the shader shape: a derived class adds a field and implements
an interface over a base class that also has a field. Removing the interface
from the inheritance list compiles on every release tested.

[Compiler Explorer](https://godbolt.org/z/KcoeM9sra) shows DXC 1.6.2112 and
trunk failing. The Clang pane rejects the `interface` keyword at parse time,
so it does not test this SROA defect.

`bug` and `crash` remain appropriate. `hlsl-next` is worth considering because
hlsl-specs#291 proposes removing `interface`; that makes the disposition a
language decision as well as a codegen one.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- The independent review was applied to all ten drafts. They remain unposted
  drafts requiring maintainer approval.
- No `reindex` or `scripts\render_overview.py` invocation was made.
- The false 4614 predicate rationale and overbroad summaries remain in
  protected evidence artifacts; this report and the reviewed comments carry
  the corrections.
- Repro quality is partial for 4527 and agent-constructed for 4615 and 4619.
  Those limitations are explicit in both verdicts and drafts.
