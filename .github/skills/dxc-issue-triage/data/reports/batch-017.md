# DXC issue triage — batch 017

**Ground truth:** local Debug compiler `main-debug`, registered at public commit
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e).
The binary self-reports
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433)`. The source tree outside the
triage workspace was not changed or rebuilt.

**Nothing was posted, edited, labelled, closed or reacted to on GitHub.**
`reindex` and `scripts\render_overview.py` were deliberately not run because
another collation session was live. Consequently, this batch received no
retroactive predicate re-scoring.

> [!IMPORTANT]
> **Sampling bias:** these nine issues are the final slice of the oldest 100
> open DXC issues. Long-lived defects, dormant enhancements and aged issue text
> are over-represented. The verdict mix does not generalise to recent issues or
> to the backlog as a whole.

## Headline

- All nine recorded statuses are `repros`; none is recommended for closure.
- Five remain compiler defects to keep open, two are never-implemented
  enhancements, and two require a maintainer or language-design decision.
- Two release regressions were measured: 4666 at v1.7.2207 and 4710 at
  v1.5.2010.
- Two issues reverse the category suggested by a quick reading: 4708 is an
  enhancement, while 4723 is a defect that silently corrupts requested output.
- Independent review reduced the nine public drafts from 4,390 to 2,735 words,
  while preserving literal diagnostics, release boundaries, symbols, caveats
  and stale-text findings.

| Issue | Recorded verdict / repro | Recorded history | Recorded action | Compiler Explorer |
| --- | --- | --- | --- | --- |
| [4648 — unsigned fixed-width typedef crash](https://github.com/microsoft/DirectXShaderCompiler/issues/4648) | `repros` / partial | `always-repro'd` | `still-valid-keep-open` | [ejc1rnGPq](https://godbolt.org/z/ejc1rnGPq) |
| [4666 — incomplete sampler-array parameter](https://github.com/microsoft/DirectXShaderCompiler/issues/4666) | `repros` / complete | `regressed-in v1.7.2207` | `still-valid-keep-open` | [1Mbe8oPcj](https://godbolt.org/z/1Mbe8oPcj) |
| [4701 — dead groupshared allocation](https://github.com/microsoft/DirectXShaderCompiler/issues/4701) | `repros` / complete | `always-repro'd` | `still-valid-keep-open` | [b9KE6as36](https://godbolt.org/z/b9KE6as36) |
| [4708 — free operator overload](https://github.com/microsoft/DirectXShaderCompiler/issues/4708) | `repros` / complete | `never-implemented` | `enhancement-not-bug` | [9esTrW5ox](https://godbolt.org/z/9esTrW5ox) |
| [4710 — resource array in cbuffer](https://github.com/microsoft/DirectXShaderCompiler/issues/4710) | `repros` / complete | `regressed` (`regressed_in=v1.5.2010`) | `needs-human-judgement` | [EKh5E8Y4M](https://godbolt.org/z/EKh5E8Y4M) |
| [4721 — apply Clang fix-its](https://github.com/microsoft/DirectXShaderCompiler/issues/4721) | `repros` / agent-constructed | `never-implemented` | `enhancement-not-bug` | [af7P4dYvc](https://godbolt.org/z/af7P4dYvc) |
| [4722 — matrix orientation on dependent types](https://github.com/microsoft/DirectXShaderCompiler/issues/4722) | `repros` / partial | `always-repro'd` | `still-valid-keep-open` | [16hP1TjKK](https://godbolt.org/z/16hP1TjKK) |
| [4723 — depfiles during preprocessing](https://github.com/microsoft/DirectXShaderCompiler/issues/4723) | `repros` / agent-constructed | `always-repro'd` | `still-valid-keep-open` | Not representable: multi-file driver outputs |
| [4763 — resources in constant buffers](https://github.com/microsoft/DirectXShaderCompiler/issues/4763) | `repros` / complete | `always-repro'd` | `needs-human-judgement` | [q9vnhdroE](https://godbolt.org/z/q9vnhdroE) |

## Text and category that no longer match behaviour

> [!CAUTION]
> These are the highest-value findings in the batch because a reader can reach
> the wrong disposition before running a compiler.
>
> - **4708:** the rejection-shaped report can be read as a compiler defect, but
>   non-member operator overloading was never an HLSL 2021 capability. It is an
>   enhancement whose proposal is now accepted for HLSL 202y. The standing
>   maintainer comment's HLSL 202x target is stale.
> - **4723:** the title asks to add support, but both flags already work
>   independently. Their combination computes the dependency rule, appends it
>   to the `-Fi` output, emits no depfile, exits 0 and gives no diagnostic. The
>   result is a corrupted requested artifact, so the measured category is a
>   defect, not an enhancement.

Other refinements are not staleness claims. 4648's title under-scopes the crash;
4722's filed test predicts the wrong failure mode; and 4763's two asks resolve
differently, but their text still describes observations that reproduce.

## Release-history cross-check

Every batch-017 matrix contains the same 20 stable tags used by batch 016,
v1.4.1907 through v1.9.2607. Catalog paths cover both physical roots:
`.cache\compilers\releases\` and
`build\tools\clang\test\dxc_releases\`; no arm64 executable appears in the
catalog.

| Check | Independent result |
| --- | --- |
| 4666 regression | Five stable releases through v1.6.2112 accept; the 15 releases from v1.7.2207 reject. |
| 4710 regression | v1.4.1907 accepts; all 19 later stable releases reject. This is the same 1/19 split and v1.5.2010 boundary independently measured for batch-016 issue 4615. |
| SM 6.6 floor | 4710's as-filed `ps_6_6` form starts at v1.6.2104, agreeing with batch-016 issue 4520. Retargeting to `ps_6_0` is what exposed the older clean release. |
| HLSL 2021 floor | 4708 and 4722 independently count 16 capable releases from v1.6.2112. 4721's capability column agrees. |
| `-MF` floor | 4723 finds five unsupported releases and 15 measurable releases from v1.7.2207. Its result stays flat across the v1.7.2212 `-P` spelling transition, which is also a measured boundary in batch-016 issue 4619. |
| Always-reproducing cases | 4648, 4701 and 4763 each cover all 20 stable releases; their per-release controls also cover all 20. |

No outcome or release count conflicts with batch 016. One metadata inconsistency
does remain: 4723's generated history labels its date column with GitHub
publication dates, while the catalog and the other matrices order and label
releases by asset build date. The tags and outcomes are unaffected.

## Evidence verification and factual corrections

- The method from `issues/4721/check-quotes.py` was run read-only over all nine
  drafts. Forty fenced or output-shaped fragments were checked after stripping
  ANSI colour; all forty occur byte-for-byte in captured `.txt` evidence.
- All eight Compiler Explorer links returned HTTP 200. 4723 correctly records
  a skip because Compiler Explorer cannot show its multi-file filesystem
  observable.
- Live read-only GitHub checks confirm proposal 0008 currently says
  `status: Accepted` and `Planned Version: 202y`; commits `19492299e`
  (2025-04-01) and `9185c3884` (2025-07-22) record the retarget and acceptance.
- All nine `batch` values are `batch-017`. Required provenance was merged with
  `triage.py verdict`: `triaged_by=claude-opus-5` and
  `reviewed_by=gpt-5.6-sol`. The command also refreshed `triaged_at`; no
  measurement or other verdict field was changed.

The review found several conclusions whose long-form evidence is sound but
whose compressed artifact wording is not:

1. **4666:** the verdict summary says “any non-templated builtin object type”;
   only three such types were tested. The reviewed draft names those three.
2. **4666:** notes and the worker draft claimed the adjacent ICE reached
   v1.6.2112 and quoted a release-mode access-violation line, but the directory
   contains only the current Debug subject/control captures. The reviewed
   draft is limited to that recorded measurement.
3. **4710:** `history` is the off-taxonomy short value `regressed`, although
   `regressed_in` correctly records v1.5.2010. This was reported rather than
   edited under the evidence-write boundary.
4. **4710:** the verdict summary attributes the regression to `94460c988` more
   firmly than the notes permit. The 434-commit window and lack of a direct
   commit build support “strong lead,” not proof.
5. **4721:** the verdict summary says `dxr` “silently” drops the initializer.
   It exits 0 and emits truncated output, but stderr contains the diagnostic
   and fix-it hint. The reviewed draft removes the unsupported adverb.
6. **4722:** the summary's opening claim that orientation “never reaches” a
   dependent matrix is too broad because the same summary and controls show
   `-Zpr` works. The reviewed draft scopes the failure to pragma/type
   annotation paths.
7. **4648:** “any user typedef” overstates a matrix containing one user typedef
   plus the three fixed-width aliases. The reviewed draft lists only measured
   cases.

These do not change a substantive verdict.

## Per-issue findings

### 4648 — fixed-width typedef crash

The access violation reproduces on all 20 stable releases. Older releases
crash with empty stderr, demonstrating why the `internal_failure` predicate
must not anchor on current diagnostic text. The crash also affects locals,
parameters, struct members, 32/64-bit aliases and a plain user typedef.
Priming the corresponding unsigned scalar type suppresses the null lookup.

### 4666 — incomplete builtin-object array parameter

The primary diagnostic regressed at v1.7.2207 and is order-dependent type
completion, not a sampler-only restriction. The SPIR-V half is older than its
validator boundary: v1.6.2104 emits the same invalid `OpTypeStruct`, but its
bundled SPIRV-Tools does not reject it. A `[noinline]` requirement is
load-bearing. The struct workaround also exposes a separately controlled DXC
ICE on the current Debug build.

### 4701 — groupshared dead-store gap

The TGSM allocation and store survive on every stable release, while identical
static and function-local controls are removed on every release. At 64 KB the
missed optimisation becomes a validation failure. FXC removes the allocation;
DXC and the Clang HLSL front end retain it. Source guards in `GlobalOpt` and
`IsStaticGlobal` explain the gap without proving a preferred fix.

### 4708 — never-implemented language feature

The four pre-HLSL-2021 releases are unmeasurable; all 16 capable releases reject
the free operator while the member-operator control compiles. v1.8.2403 added
a clearer declaration-site diagnostic. Clang trunk accepts and evaluates the
operator, but the artifacts do not establish whether that is deliberate
proposal-0008 support or inherited C++ behaviour.

### 4710 — resource-array indexing regression

v1.4.1907 and FXC `ps_5_0` produce the expected `t0/t5/t10/t15` bindings;
v1.5.2010 and every later stable release emit the literal-index diagnostic.
`-dxilgen` runs before `-dxil-loop-unroll`, so `[unroll]` cannot satisfy the
guard. Whether the binding restriction is intended remains a design decision.
Clang trunk separately crashes in `CGHLSLRuntime::emitBufferCopy`.

### 4721 — fix-it application surface

Every stable release rejects `-fixit`, although DXC has printed the replacement
hint since v1.7.2207. The rewriter/action code is present and linked, but no dxc
driver option selects it. A different Clang fork applies fix-its; this tree's
optional `clang.exe` path was deliberately not built. `dxr` also exits 0 while
dropping the diagnosed initializer, and ten historical releases could not
compile their own suggested `and(a,b)` replacement.

### 4722 — dependent matrix orientation

`#pragma pack_matrix` is silently ignored on dependent matrix members, while
an explicit qualifier is rejected at template definition time. Opposite
requests produce byte-identical containers, concrete controls differ, and
`-Zpr` works. All 16 HLSL-2021-capable stable releases reproduce.

### 4723 — depfile output corrupts preprocessing output

With `-P -Fi ... -MF ...`, the depfile is missing and its 63-byte dependency
rule is appended to the `.i` file. The run exits 0 without a diagnostic and
the resulting file no longer compiles. All 15 releases with `-MF` behave
identically. The five older releases are unsupported probes.

### 4763 — deliberate acceptance, incorrect layout

Resources in cbuffers are accepted silently on all 20 releases, and the
validator accepts the container. That acceptance is a deliberate compatibility
decision requiring language judgement. The `StructuredBuffer<T>` size and
offsets are separately wrong: DXC charges `sizeof(T)`, while FXC charges zero.
The earlier `Buffer<T>` version of that layout bug was fixed between
v1.6.2104 and v1.6.2106.

## Adjacent defects

These findings are not the primary issue under test and should not be filed by
this read-only pass.

| Source | Adjacent finding | Repro and control evidence | Owner |
| --- | --- | --- | --- |
| 4350 (earlier batch) | A `const` local accepts the same forbidden mutation silently, separate from the cbuffer-backed ICE. | `issues/4350/control-const-local.hlsl`, `variant-control-constlocal-main-debug.txt`; mutable and syntax-error controls in `control-static-obj.hlsl` / `control-syntax-error.hlsl` and their captures. | DXC front end |
| 4351 (earlier batch) | `-remove-unused-globals` deletes an unused function-parameter type while retaining the signature, distinct from the array-member case in the issue body. | `issues/4351/case-fn-param.hlsl`, `variant-fn-param-main-debug-rw--match-fn-param.txt`; the retained, read parameter type is the in-run control. | DXC rewriter |
| 4666 | The non-inlined struct workaround ICEs instead of diagnosing. | `issues/4666/observation-noinline-struct-sampler-array.hlsl`, `variant-noinline-struct-ice-main-debug--match-noinline-struct-ice.txt`; scalar-member control and capture beside them. | DXC |
| 4710 | `hlsl_clang_trunk` crashes in `CGHLSLRuntime::emitBufferCopy`; removing the resource member compiles. | `issues/4710/manual-case-clang-control.txt`, generated by `probe-clang-control.py`. | Clang HLSL front end |
| 4721 | `dxr` exits 0 and emits `bool4 mask;`, dropping the diagnosed initializer; the fixed-input control preserves it. | `issues/4721/variant-rewriter-main-debug-rw--match-rewrite.txt` and `variant-rewriter-control-main-debug-rw--match-rewrite.txt`. | DXC rewriter |
| 4721 (historical) | v1.7.2207–v1.8.2407 print `and(a,b)` as a fix-it but reject it with `Invalid record`, including under `-Vd`; v1.8.2502 fixes that behaviour. | `issues/4721/control-fixed.hlsl`, `manual-case-release-matrix.txt`; separate HLSL-2021 capability column and validation-disabled arm. | DXC |

4763's measured `Buffer<T>` transition is a fixed historical precedent rather
than a new adjacent defect. 4701's nearby #6417 and 4723's #5416 already have
issues. 4527's changed rejection is the current form of its source issue, not a
separate unfiled defect.

## Independent draft review

All nine worker drafts were reviewed on `gpt-5.6-sol`, different from the
`claude-opus-5` authors. Concision was primary; edits were applied in place.

| Issue | Applied edit and reason |
| --- | --- |
| 4648 | Reduced 517 words to 200; removed named-person corrections, pseudo-verbatim ellipsis paths, universal typedef language and an unsupported `incorrect-code` label rationale. Kept the exact crash, null-type mechanism, broadened cases and priming control. |
| 4666 | Reduced 587 words to about 385; scoped the builtin claim to three tested types, removed reconstructed source blocks and the uncaptured release ICE quote/history. Kept both release boundaries, `[noinline]` caveat and current adjacent crash. |
| 4701 | Reduced 597 words to about 310; removed repeated A/B narration and fabricated command/ellipsis lines from quoted blocks. Kept exact IR, the 64 KB diagnostic, paired history and named pass guards. |
| 4708 | Reduced 469 words to 236; led with enhancement status and the stale 202x target, retained exact DXC/Clang output and the intentionality caveat, and removed rhetorical disposition language. |
| 4710 | Reduced 422 words to about 295; replaced reconstructed ellipsis IR with the literal diagnostic, softened exact-commit attribution, and retained the pass-order evidence, design question and controlled Clang crash. |
| 4721 | Reduced 412 words to about 315; removed effort speculation, retained the unbuilt-own-tree caveat and exact external Clang quote, and preserved both rewriter hazards. |
| 4722 | Scoped the lead to 16 capable releases, replaced a partial diagnostic with an exact captured line, removed a test-case typo aside, and retained the two failure modes and working `-Zpr` control. |
| 4723 | Reduced 549 words to 373; led with the category reversal, replaced an uncaptured “file not found” quote with exact harness lines, removed speculative cross-issue fix claims, and retained the untested API caveat. |
| 4763 | Reduced 449 words to about 280; removed an uncaptured version fragment, source-code block and all alignment-comment discussion. The final draft is additive and contains no residue of the earlier attempted correction of a named contributor. |

## What this batch taught about the method

1. **`never-implemented` is a necessary history value.** 4708 and 4721 coined
   it independently. `always-repro'd` would falsely call correct rejection a
   compiler defect.
2. **Release enumeration must come from `releases.cached_path`.** Two cache
   roots, arm64 binaries and nonuniform archive layouts make filesystem walks
   silently wrong.
3. **The measurement instrument has history too.** A PSV field, an IR spelling
   or a disassembler anchor can manufacture a boundary at either end of the
   range. Verify anchors on known-good oldest and newest compiles.
4. **A release boundary may belong to a bundled validator.** 4666's SPIR-V
   diagnostic changed while the emitted invalid module did not. Separate
   emission from validation.
5. **Use the oldest sufficient profile before history work.** 4710's filed
   `ps_6_6` command would have hidden the only clean release and inverted the
   conclusion.
6. **Diagnostic-shaped symptoms require per-release capability controls.**
   `invalid-probe` cannot distinguish the requested diagnostic from an
   unrelated old-feature rejection.
7. **Record predictions before measuring.** Falsified controls found the 4666
   ICE and disproved 4648's title-level scope assumptions.
8. **Never contradict a named person from source reading alone.** 4763's
   measured nested-layout control proved the contributor right; the corrective
   draft was removed.
9. **Quote fidelity should be a mechanical gate.** ANSI colouring,
   reconstructed slashes and edited ellipses all produce plausible fabricated
   output. The 4721 checker caught this class and generalized cleanly.
10. **File-output issues need harness controls.** Capture complete files,
    sizes, both ends and true subprocess status; `%ERRORLEVEL%`, `.cmd`
    HRESULTs and truncated heads all lied on 4723.
11. **Adjacent findings need a first-class artifact.** Triage repeatedly
    produces controlled, unfiled defects that disappear inside source-issue
    notes unless the batch aggregates them.
12. **A shared ground-truth build is mutable state.** 4721 correctly left the
    optional `clang.exe` question unanswered rather than relink while peers
    were measuring.
13. **Hazards should be questions, not predictions.** Open wording caused 4648
    to test and refute title assumptions rather than confirm them.
14. **Evidence in a terminal does not exist.** If prose names a command, its
    output needs a durable capture before the verdict is written.

## Timeline integrity

Read-only timeline checks found only pre-existing cross-references:

- 4648: one, dated 2022-09-20 (#61).
- 4708: one, dated 2023-11-30 (#6081).
- 4722: one, dated 2022-10-13 (#2499).
- 4723: two, dated 2023-06-30 (#3863) and 2023-07-13 (#5416).
- 4763: one, dated 2024-04-30 (#225).
- 4666, 4701, 4710 and 4721: none.

Every event predates batch 017. No cross-reference was created by this work.

## Reconstruction gaps

- The claimed release reach-back of 4666's adjacent ICE cannot be reconstructed
  from the directory. Only the current Debug repro/control are captured.
- Proposal 0008's status and dates were independently verified live, but the
  worker left no raw API or source snapshot in the issue directory.
- The required in-place review leaves no byte-for-byte worker-draft snapshot.
  The review table records every semantic edit, not an exact line diff.
- 4708's maintainer-comment version staleness is recorded in `text_stale`;
  4723's category reversal is report-only because allowed verdict edits in this
  collation were limited to provenance and reviewer metadata.
- 4710's malformed `history` value remains visible rather than silently
  normalized. Its separate `regressed_in` field and captures make the intended
  boundary reconstructable.

## Verification

- `triage.py audit --issue <n>` reported `no missing evidence` for each of the
  nine issues.
- `check_paths.py` passed: 5,443 committable text files, 16 allowlisted
  matches in four files, and no unexpected machine paths.

## Proposed issue comments

These are **drafts for review, not posted**. No comment, label or state change
has been made on any issue. Each is written to be postable as-is by a maintainer.
Compiler-behaviour claims are backed by captured evidence in `issues/<nnnn>/`;
the one live proposal-status check without a preserved snapshot is identified
under Reconstruction gaps.

They deliberately avoid promising fixes or timelines, and where the next step is a product or
language decision they say so rather than pre-empting it. Quoted compiler output was
re-verified before being written down.

Each draft ends with a trailer disclosing that it came from an assisted triage pass.

Source of each is `issues/<nnnn>/comment.md` — edit there, then re-run
`scripts/render_comments.py <batch>` to refresh this section.


### Draft — [#4648](https://github.com/microsoft/DirectXShaderCompiler/issues/4648) unsigned int{16,32,64}_t at global scope causes Segfault (attempted to read from 0x8)

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4648](https://github.com/microsoft/DirectXShaderCompiler/issues/4648).

Still reproduces on `main` (`13730886e`) and on all 20 stable releases from
v1.4.1907 through v1.9.2607. The oldest two exit with `0xC0000005` and empty
stderr; v1.6.2104 onward print:

```text
Internal compiler error: access violation. Attempted to read from address 0x0000000000000008
```

The Debug build first hits the `DeclSpec.cpp:640` and `Type.h:581` null-type
asserts; continuing reaches the same access violation. In
`HLSLExternalSource::ApplyTypeSpecSignToParsedType`,
`return m_scalarTypes[newScalarType];` can return a null lazily-created scalar
type. Naming the corresponding unsigned type earlier primes that slot and makes
the unchanged declaration compile.

The defect is broader than the title: locals, parameters, struct members,
`unsigned int32_t`, `unsigned int64_t`, and
`typedef int MyInt; unsigned MyInt g;` also crash. Vector and matrix spellings
escape because `LookupVectorType`/`LookupMatrixType` perform the scalar lookup
first. The only in-tree coverage is for those working shorthand forms.

[Compiler Explorer](https://godbolt.org/z/ejc1rnGPq) shows DXC trunk and
v1.6.2112 crashing while the primed control compiles; Clang-HLSL rejects the
construct instead.

Suggested label: add **`type-system`**; `bug` and `crash` already fit.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4666](https://github.com/microsoft/DirectXShaderCompiler/issues/4666) Variable has incomplete type 'SamplerState [2]'

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#4666](https://github.com/microsoft/DirectXShaderCompiler/issues/4666).

Still reproduces on `main` (`dxcompiler.dll: 1.10(5433-ab540090)`). It is a regression, and the
boundary is **v1.7.2207**: the five stable releases through v1.6.2112 accept the repro; all
15 later releases reject it.

Repro, v1.6.2112 next to trunk: https://godbolt.org/z/1Mbe8oPcj

```text
repro.hlsl:12:61: error: variable has incomplete type 'SamplerState [2]'
```

The three tested non-templated builtin types—`SamplerState`,
`SamplerComparisonState`, and `ByteAddressBuffer`—fail in array parameters;
the tested templated texture types compile. Scalar parameters also compile.
The reported struct workaround is really declaration ordering: an earlier
declaration that requires type completion suppresses the error, while the same
declaration later, or a typedef that merely names the array, does not.

That points at the on-demand completion introduced by #4317, which made builtin object types
start life incomplete and be completed by `HLSLExternalSource::CompleteType`, and the array-element
completion added in `Sema::RequireCompleteTypeImpl` by #4379. Both land inside the
v1.6.2112 → v1.7.2207 window. The test added with #4379,
`tools/clang/test/HLSLFileCheck/hlsl/template/complete-array-parameter.hlsl`, covers
`Texture2D f[2]` only—the working templated case. Intermediate commits were not
built, so this is a lead rather than a bisect.

**On the SPIR-V half.** It still reproduces, but the module has been invalid for longer than it
looks. v1.6.2104 emits the same `%Test = OpTypeStruct %_arr_type_sampler_uint_2` and exits 0,
because its bundled SPIRV-Tools predates `VUID-StandaloneSpirv-None-04667`. So the apparent
v1.6.2106 boundary is a validator upgrade, not a compiler change — DXC has emitted this for as
long as it can be measured. Reproducing it also needs `[noinline]`; otherwise the helper is
inlined and the struct type is never emitted.

**Adjacent defect:** suppressing inlining on the struct workaround crashes the
current Debug build with `Internal compiler error: LLVM Assert`. Replacing the
sampler array with a scalar produces an ordinary resource-pointer diagnostic,
so the array in the aggregate is the discriminating variable.

**Labels:** suggest adding `type-system` and `diagnostic` — correct code is rejected because of an
inconsistency in when builtin object types are completed. `spirv` is right for the second half but
the primary symptom is front-end and shows up identically for DXIL, so this may need an owner
outside the SPIR-V area.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4701](https://github.com/microsoft/DirectXShaderCompiler/issues/4701) DXC not optimizing out code related to groupshared

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4701](https://github.com/microsoft/DirectXShaderCompiler/issues/4701).

Still reproduces on `main` (`13730886e`) and all 20 stable releases from
v1.4.1907 through v1.9.2607. The final DXIL still contains both the reported
TGSM allocation and its never-read store:

```llvm
@"\01?a@@3PAMA" = external addrspace(3) global [10 x float], align 4
  store float 1.000000e+00, float addrspace(3)* getelementptr inbounds ([10 x float], [10 x float] addrspace(3)* @"\01?a@@3PAMA", i32 0, i32 0), align 4, !tbaa !7
```

The identical `static` and function-local arrays are removed on every one of
those releases, while a genuinely live `groupshared` control remains visible.
The result is unchanged at the default `-O3`, `-O1`, and `-Od`.

This has a compile-time consequence. Scaling the dead TGSM array to 64 KB
produces:

```text
case-budget-groupshared.hlsl:9:10: error: Total Thread Group Shared Memory used by 'main' is 65536, exceeding maximum: 32768.
```

The static twin compiles to `ret void`. Whether the budget should be checked
before or after this optimisation is a design question; no GPU/runtime effect
was measured.

**Other compilers.** FXC (`fxc /T cs_5_0`) removes it entirely — no `dcl_tgsm`, ~1 instruction
slot. The clang-based HLSL front end currently keeps it, same as DXC. All panes:
<https://godbolt.org/z/b9KE6as36>

`-fcgl` shows why the generic passes miss it: TGSM is emitted as an external
address-space-3 global with no initializer, while the static twin is an
internal initialized global. `GlobalOpt::ProcessGlobal`
(`GlobalOpt.cpp:1707,1720`) rejects the former, and
`LowerStaticGlobalIntoAlloca` requires `IsStaticGlobal`
(`DxilUtil.cpp:114`), which excludes address space 3. A safe fix still needs
module-wide liveness because a TGSM store is dead only when no load exists.

Suggested label: `fxc-disagrees` alongside the existing `performance`. No `check-in-clang` —
clang was checked and behaves the same.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4708](https://github.com/microsoft/DirectXShaderCompiler/issues/4708) Free operator overload

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4708](https://github.com/microsoft/DirectXShaderCompiler/issues/4708).

**This is an enhancement, not a DXC defect.** Non-member operator overloading
was never an HLSL 2021 capability. The feature has since been accepted in
[hlsl-specs proposal 0008](https://github.com/microsoft/hlsl-specs/blob/main/proposals/0008-non-member-operator-overloading.md),
targeting **HLSL 202y**. The standing 2023 comment's **202x** target is now
stale.

Current DXC rejects the declaration deliberately:

```text
repro.hlsl:15:12: error: overloading non-member 'operator+' is not allowed
```

All 16 stable releases that can express HLSL 2021 templates reject the free
operator while the member-operator control compiles; the four older releases
are unmeasurable, not clean. v1.8.2403 added the declaration-site diagnostic
above; that was a diagnostic improvement, not a regression.

Clang trunk compiles the issue shader. An observable variant proves the
operator is resolved and evaluated:

```llvm
  call void @dx.op.bufferStore.f32(i32 69, %dx.types.Handle %1, i32 %2, i32 0, float 4.000000e+00, float undef, float undef, float undef, i8 1), !dbg !134
```

Side-by-side evidence: <https://godbolt.org/z/9esTrW5ox>. This establishes
Clang's current behaviour, but not whether it is an intentional implementation
of proposal 0008 rather than inherited C++ overload resolution.

Suggested disposition: keep open as an accepted language feature (`hlsl-next`
plus `enhancement`), or consolidate with the spec proposal if it is not planned
for DXC itself.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4710](https://github.com/microsoft/DirectXShaderCompiler/issues/4710) Incorrectly erroring with error: Index for resource array inside cbuffer must be a literal expression

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4710](https://github.com/microsoft/DirectXShaderCompiler/issues/4710).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`), and it is a **regression**: v1.4.1907
compiles this shader; v1.5.2010 is the first release that rejects it, and every release since
does. The 20-release scan ran three positive controls on every binary.

```text
repro.hlsl:25:41: error: Index for resource array inside cbuffer must be a literal expression
```

v1.4.1907 emits handles at `t0`/`t5`/`t10`/`t15`, as the loop requires.
FXC `ps_5_0` independently produces the same binding layout; FXC `ps_5_1`
fails as described in the thread. All panes:
<https://godbolt.org/z/EKh5E8Y4M>.

**Why `[unroll]` cannot help.** The check is in a DXIL-lowering pass, not in Sema —
`HLModule::GetBindingForResourceInCB` (`lib/HLSL/HLModule.cpp:816`) rejects a GEP that
`!hasAllConstantIndices()`. `dxc -Odump` places `-dxilgen` at index 36 and
`-dxil-loop-unroll` at 41, so the guard runs before `[unroll]`; `-fcgl`
accepts the shader.

`git log -S` strongly points to `94460c988`, which introduced per-element
resource binding and rewrote `resource-in-cb4.hlsl` from a passing binding
table to an expected diagnostic. It is inside the 434-commit release window;
the exact commit was not built.

The remaining question is whether the guard is too strict or intentionally
rejects a binding model that cannot represent the pre-unroll index. The output
does not settle that design decision.

**Also worth a separate issue:** Clang trunk in DXC mode *crashes* on this shader in
`CGHLSLRuntime::emitBufferCopy`. The same shader with the resource member removed compiles
cleanly, so the crash tracks the resource-in-cbuffer copy specifically.

Suggested labels: `bug` (a measured regression), `diagnostic` (the symptom is the diagnostic
itself), `check-in-clang` (checked — it crashes, and that needs its own fix).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4721](https://github.com/microsoft/DirectXShaderCompiler/issues/4721) Support applying clang fix-its automatically

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4721](https://github.com/microsoft/DirectXShaderCompiler/issues/4721).

Still open and still accurate, but the gap is narrower than the title
suggests: `dxc` already computes fix-its and prints them — there is just no
way to ask it to apply them.

On `main` (`13730886`):

```text
dxc failed : Unknown argument: '-fixit'

repro.hlsl:12:18: error: operands for short-circuiting logical binary operator must be scalar, for non-scalar types use 'and'
  bool4 mask = a && b;
               ~~^~~~
               and(a, b)
```

`and(a, b)` is a `FixItHint::CreateReplacement` from `SemaHLSL.cpp:10713`, and
pasting it in compiles clean. All 20 stable releases v1.4.1907–v1.9.2607
reject `-fixit`; on this build so do `-fixit=hlsl`, `-fixit-recompile` and
`-Xclang`, and `-help` documents none of them. (`/fixit` "succeeds" only
because dxc silently drops unrecognised `/`-flags: it produces an object
byte-identical to no flag at all.)

The machinery is in the tree and already linked into `dxcompiler`:
`FixItRewriter.cpp` in `clangRewriteFrontend`, `case FixIt: return new
FixItAction();` in `ExecuteCompilerInvocation.cpp:53`, `-fixit` still declared
in `CC1Options.td:396`. What is missing is a driver route to it —
`HLSLOptions.td` declares neither `fixit` nor `Xclang`, so nothing selects
that action.

llvm-project's HLSL clang exposes `-Xclang -fixit` and reports:

```text
<source>:12:17: note: FIX-IT applied suggested code changes
```

That is a different fork, so this tree's inherited `-cc1 -fixit` path remains
unmeasured; proving it would require building the optional `clang.exe`.
[Compiler Explorer](https://godbolt.org/z/af7P4dYvc) shows both compilers.

Two implementation caveats are already measurable. First, `dxr` prints the
same hint and exits 0 but emits `bool4 mask;`; the fixed-input control preserves
`bool4 mask = and(a, b);`. Second, from v1.7.2207 through v1.8.2407 the
suggested replacement itself fails with `error: Invalid record`, even under
`-Vd`; it compiles from v1.8.2502.

Suggested labels: `enhancement`, `diagnostic`, and `rewriter`, alongside
`hlsl-next`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4722](https://github.com/microsoft/DirectXShaderCompiler/issues/4722) `column_major` and `row_major` don't apply correctly to template-dependent types

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4722](https://github.com/microsoft/DirectXShaderCompiler/issues/4722).

Still reproduces on `main` (`dxcompiler.dll 1.9.0.5433`, `13730886e`) and all
16 stable releases that can compile HLSL 2021 templates, from **v1.6.2112**.
The four older releases are unmeasurable, not clean.

There are two failures, depending on how orientation is requested.

**1. `#pragma pack_matrix` is silently dropped.** Both members below are 4x4 float matrices in
one cbuffer under one pragma; only the non-template one gets the requested layout:

```
;   struct hostlayout.CB
;       struct hostlayout.struct.ThroughTemplate<float, 4, 4>
;           column_major float4x4 M;                  ; Offset:    0
;       } A;
;       struct hostlayout.struct.Directly
;           row_major float4x4 M;                     ; Offset:   64
;       } B;
```

[Compiler Explorer](https://godbolt.org/z/16hP1TjKK) (dxc 1.6.2112 and trunk agree). Compiling
the template's `row_major`, `column_major`, and no-pragma forms produces
byte-identical containers. The same concrete pair differs, so the instrument
can detect orientation and the template is the discriminating variable.

**2. The test case in the report doesn't compile.** The two lines expected to succeed are
rejected:

```text
repro-explicit-qualifier.hlsl:18:3: error: 'row_major' can only be used with a matrix type
  row_major matrix<T, X, Y> RowMajor;
```

This fires at template *definition* time, so it also rejects `row_major T M;` when `T` is
instantiated as `float4x4` — it is testing dependence, not matrix-ness. Conversely, the four
`expected-error` directives in the filed test all fire, so its
missing-diagnostic half does not reproduce.

**`-Zpr` works correctly on template-dependent members.** That may be the useful lead: per the
comment at `SemaType.cpp:4353`, the flag is applied through the codegen default while
`#pragma pack_matrix` is applied by annotating the type in `GetTypeForDeclarator`, guarded by
`hlsl::IsHLSLMatType`. That guard canonicalises and asks for a `RecordType`
(`HlslTypes.cpp:56`), which a dependent `matrix<T,X,Y>` is not — so the pragma never attaches.
`SemaType.cpp:5820` uses the same matrix-ness test to *reject* an explicit qualifier, which is
failure 2. One predicate, two consequences.

Suggested labels: **correctness** (silently wrong layout) and **type-system**
(the parse-time matrix test on a dependent type).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4723](https://github.com/microsoft/DirectXShaderCompiler/issues/4723) Support -M depfile generation flags during -P preprocess to file

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4723](https://github.com/microsoft/DirectXShaderCompiler/issues/4723).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and it is worse than
"unsupported": under `-P`, the `-M` family writes no depfile and instead
appends the dependency list to the preprocessed output, silently corrupting it.

This changes the issue's category: the title reads as an enhancement request,
but the measured behaviour is a defect in an already-supported flag
combination.

```text
dep4723-artifact depfile-MF dep-preprocess.d MISSING
dep4723-artifact preprocessed-P repro.i PRESENT bytes=354
dep4723-tail repro.i | repro.hlsl: repro.hlsl \
dep4723-tail repro.i |  inc/common.hlsli \
dep4723-tail repro.i |  inc/nested.hlsli
```

Without `-MF`, the same preprocessed file is 291 bytes. The 63-byte
difference is exactly the dependency rule. Feeding the contaminated file back
to DXC produces:

```text
repro.hlsl:9:1: error: unknown type name 'repro'
repro.hlsl: repro.hlsl \
^
```

The `-P` run itself exits 0 with no diagnostic; `-MD` and `-M` behave the same.
The flag is parsed: an invalid `-MF` path is diagnosed in compile mode and
silently accepted under `-P`.

- `DxcContext::Preprocess()` (`dxclib/dxc.cpp`) writes the result blob straight to `-Fi` and
  never reaches `ActOnBlob()`, which is the only place `-MD`/`-MF` are turned into a file.
- In `DxcCompilerObj::Compile` (`dxcompiler/dxcompilerobj.cpp`) the `isPreprocessing` branch
  and the `opts.DumpDependencies` branch both write to the same `outStream`, and the second is
  not suppressed when the first has run.

`HLSLOptions.cpp` already warns for other output flags under `-P`; the `-M`
family is absent from that list.

Unchanged for the life of the issue: v1.7.2207 through v1.9.2607 and `main`
all produce the same 354-byte contaminated file. The five older stable
releases lack `-MF`, so they are unmeasurable rather than clean.

Labels: `bug` and `high-impact` still fit — the corruption is silent and the workflow it breaks
is the one the issue describes. Suggest adding `diagnostic`, since the smallest useful change
here is a warning that these flags are inert under `-P`. Whether to implement the depfile
support itself is a product call.

Compiler Explorer cannot represent this repro: the observable is a multi-file
set of driver outputs, not a single compiled result. Only `dxc.exe` was
measured; the equivalent `dxcompiler.dll` API path remains untested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4763](https://github.com/microsoft/DirectXShaderCompiler/issues/4763) DXC doesn't report an error when placing a resource in a ConstantBuffer

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4763](https://github.com/microsoft/DirectXShaderCompiler/issues/4763).

Still reproduces on `main` (`13730886e`) and all 20 stable releases from
v1.4.1907 through v1.9.2607. The original offsets and sizes are still exact:

```text
;           uint myInt;                               ; Offset:   12
;   } __cbModelData2;                                 ; Offset:    0 Size:    16
;           uint myInt;                               ; Offset:   64
;   } __cbModelData3;                                 ; Offset:    0 Size:    68
```

Exit 0, no diagnostic. `dxv` on the container returns `Validation succeeded.`, so nothing
downstream catches it either.

Compiler Explorer, four panes on one source — `fxc_10_0_19041 /T ps_5_0`, `dxc_1_6_2112`,
`dxc_trunk`, and `hlsl_clang_trunk -fsyntax-only`: <https://godbolt.org/z/q9vnhdroE>

The report's two asks resolve differently. The missing diagnostic reflects a
deliberate compatibility decision: commit
[`2b4f3e4`](https://github.com/microsoft/DirectXShaderCompiler/commit/2b4f3e4801fa602322111f0a28357a400b4a6ab5)
made scalar resources in cbuffers legal and retained an error only for view
arrays. That array control is diagnosed on every release:
`error: object types not supported in cbuffer/tbuffer view arrays.` Whether
scalar resources should instead be rejected remains a language decision tracked
by [hlsl-specs#225](https://github.com/microsoft/hlsl-specs/issues/225).

The layout is a concrete bug. FXC is also silent, but gives every cbuffer
`Size: 4` with `myInt` at offset 0. DXC's
`CGMSHLSLRuntime::AddTypeAnnotation` condition at `CGHLSLMS.cpp:1282`
excludes `StructuredBuffer<T>` from the zero-size resource rule and charges
`sizeof(T)`.

`Buffer<T>` had the same bug until
[`e6ba792`](https://github.com/microsoft/DirectXShaderCompiler/commit/e6ba792e2);
the measured transition is v1.6.2104 to v1.6.2106, while
`StructuredBuffer<T>` remains wrong.

Suggested labels: `bug`, `correctness` (a host writing at the FXC-derived offsets writes to
the wrong place), `diagnostic`. Keeping `fxc-disagrees`, which the layout comparison
justifies directly.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- Drafts are unposted and require maintainer review.
- No runtime GPU behaviour was measured.
- No method or source file was modified in this collation.
