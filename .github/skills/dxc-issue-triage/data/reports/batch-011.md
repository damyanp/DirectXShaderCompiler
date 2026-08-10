# DXC issue triage — batch 011

**Ground truth:** local Debug build, compiler-source-identical to upstream
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e6a9019e4e0823746470f3ab75341d6b)
(`1.9.0.5433`). The binary's verbatim version string contains a fork-local SHA;
that is captured build evidence, not the public citation.

**Nothing was posted, edited, labelled or closed on GitHub. No DXC compiler
source was modified.**

> [!IMPORTANT]
> **Sampling bias:** batches 011 onward are drawn exclusively from the oldest
> 100 open issues, at the user's request. The normal guidance to mix issue ages
> is deliberately suspended, though category mixing remains. These results
> describe the 2020–2022 backlog and do **not** generalise to recent issues.

## Headline

- Four requests still reproduce; three are capability or optimization
  enhancements rather than correctness bugs.
- One issue, 3362, does not reproduce when connected stages use the documented
  packing preconditions. Its attachment records different options for the two
  quoted dumps.
- 3883 remains a compiler internal failure. One defect has five observed
  presentations; the predicate was already correct and was not changed.
- 2952 and 3362 now carry `text_stale`: each issue's wording directs a reader
  toward a conclusion its own current artifacts do not support.

| Issue | Repro | History | Recommendation | Text stale | CE |
| --- | --- | --- | --- | --- | --- |
| [6727](https://github.com/microsoft/DirectXShaderCompiler/issues/6727) | `repros` / agent-constructed | all 20 stable releases | enhancement, not a bug | no | [1nG4f73d3](https://godbolt.org/z/1nG4f73d3) |
| [2952](https://github.com/microsoft/DirectXShaderCompiler/issues/2952) | `repros` / agent-constructed | all 20 stable release DLLs | enhancement, not a bug | **yes** | [YT1q1cqjb](https://godbolt.org/z/YT1q1cqjb) |
| [3362](https://github.com/microsoft/DirectXShaderCompiler/issues/3362) | `does-not-repro` / agent-constructed | no repro in all 20 stable releases | enhancement, not a bug | **yes** | [a1hKP6Tvs](https://godbolt.org/z/a1hKP6Tvs) |
| [3883](https://github.com/microsoft/DirectXShaderCompiler/issues/3883) | `repros` / complete | all 20 stable releases and `main` | keep open | no | [6c9h3r4a3](https://godbolt.org/z/6c9h3r4a3) |
| [3927](https://github.com/microsoft/DirectXShaderCompiler/issues/3927) | `repros` / complete | all 19 SPIR-V-capable stable releases | enhancement, not a bug | no | [eqxrve7j7](https://godbolt.org/z/eqxrve7j7) |

Confidence is **high** for all five.

## Reindex

The first successful pass, before shared-tool changes, reported:

```text
reindexed 55 issue(s) and 940 run(s)

evidence a completed triage should have left behind:
  #2952: verdict.json has no reviewed_by
  #3362: verdict.json has no reviewed_by
  #3883: verdict.json has no reviewed_by
  #3927: verdict.json has no reviewed_by
```

There were no changed verdicts, stale captures, or control-assertion failures.
The four lines were real evidence gaps, not noise.

After the tooling fixes, explicit historical re-probes, and independent draft
review, the final pass reported:

```text
reindexed 55 issue(s) and 950 run(s)
every probe re-scores as captured, none are stale, and no issue is missing required evidence
```

`reindex` can re-score archived text, but it cannot execute a newly added
argument-spelling retry or discover a release that was never captured. Those
cases were rerun explicitly; 3362's v1.4.1907 probe changed from an
`Unknown argument` demotion to a valid `no-repro` using `-pack_optimized`.

## The orchestrator's ten findings

### 1. Old SPIR-V releases return exit 1, not `0x80070057`

Confirmed with the repro and a trivial pixel-shader control:
v1.4.1907 and the separately checked v1.5.2003 prerelease both print
`SPIR-V CodeGen not available` and exit 1. No prior final batch report repeated
the `0x80070057` claim. SKILL.md now states the measured result.

### 2. Invalid probes must not disappear from bisection output

`bisect` now:

- reports skipped releases by reason;
- includes trimmed invalid probes in its final result;
- refuses to assign an unprobeable release inside a candidate transition to
  either side, directing the worker to `--linear`;
- distinguishes excluded prereleases from releases with no usable asset.

For 3927 the final output now says one stable release was unprobeable and five
probeable prereleases were excluded by policy. Residual limitation: a binary
search can count only invalid probes it visits. A claim about every release or
the total invalid count still requires `--linear`.

### 3. A Compiler Explorer banner can manufacture a SPIR-V hit

3927's banner now directs the reader to the decoration block and never names a
resource token whose absence is being tested. SKILL.md records that CE embeds
the compiled banner in DXIL source metadata and SPIR-V `OpSource`.

### 4. Harness bisection and missing issue authors

Both tooling defects are fixed:

- `bisect` hard-errors when the registered ground-truth executable is not
  `dxc`/`dxc.exe`, directing the worker to a fixed-harness release matrix.
- `fetch` requests the top-level issue author.

All 55 archived `issue.json` files were backfilled with `author`. Public
attributions were spot-checked where a draft relied on an external thread:
the 3005 fix PR is by `adam-yang`, and the 3237 quotations from issue 657 are
by `pow2clk` and `tex3d`.

### 5. Absence and presence predicates need self-tests in the predicate

Promoted to SKILL.md in both directions.

- 2952's predicate requires `field-search-selftest=pass`, proving the same
  enumeration can find a known field before accepting "payload size absent".
- 3927 requires a fragment `OpEntryPoint` plus the binding decorations, and a
  dead-resource control proves the predicate is not matching any successful
  module that declares the names.
- 6727's source-embedding control makes the absent op-class token visible and
  proves its `not_regex` clause can fail.

### 6. 3362 was blindly re-derived and its tone was rewritten

The blind pass was not shown the worker's conclusion. It independently found:

- `attach/domain_pack_optimized` records optimized packing;
- `attach/pixel_pack_optimized` does not;
- equal structs and equal options produce matching DS/PS layouts;
- asymmetric signatures provide a positive mismatch control.

The public draft now leads with the constructive documentation/diagnostic gap,
describes the two command lines neutrally, and makes no claim about the
reporter. D3D12 PSO creation itself was not rerun; the verified compiler result
is signature agreement under matching preconditions.

### 7. `Unknown argument` can be a spelling difference

`run` now retries `-`/`_` and `-`/`/` spellings before preserving an
`invalid-probe`, recording both requested and accepted commands. The stale
capture check compares `cmd.txt` with the requested command.

Known earlier cases were rechecked:

- 3189 still cannot be measured on v1.4.1907: after removing the reconstructed
  shift flag, a flag-free control reaches `SPIR-V CodeGen not available`.
- 8732 already treated old releases as unmeasurable, not as clean evidence.
- 3362 was the genuine false demotion and now has a valid v1.4.1907 result plus
  a positive control on that release.

No prior stable-release verdict moved.

### 8. 3883's predicate was correct; its prose was not

The predicate remains `internal_failure`. Its implementation combines:

- structured internal-failure statuses, including `0x80AA001C` and
  `0x80AA001D`; and
- the build-agnostic `(?:llvm::)?cast<...>() argument` marker when a release
  flattens the failure to ordinary E_FAIL.

The prose now reports five presentations: silent access violation, messaged
access violation, `0x80AA001D`, E_FAIL plus the cast marker, and the Debug LLVM
assert. An ordinary diagnosed E_FAIL remains a `no-repro`, which is the fix
shape the issue asks for.

### 9. Prereleases are excluded by policy, with one carve-out

The superseding user policy materially narrows the original finding 9.
`bisectable=0` for prereleases is correct, stable releases define the reported
boundaries, and **no prior batch history needed reopening on account of
prereleases**. The defect was silence about the exclusion, not the exclusion.

The final implementation follows that policy:

- stable releases define history boundaries;
- skipped prereleases are named and counted, never silently treated as passed;
- a usable prerelease enters the sequence only when the issue explicitly names
  it **and** `release-policy.json` records a per-issue opt-in;
- `bisect` validates the artifact against the issue text rather than inferring
  an exception from the filing date or text alone;
- being current when the issue was filed is not sufficient.

None of this batch's three hand-run v1.5.2003 probes qualifies for the
exception:

| Issue | What the filing names | Headline history |
| --- | --- | --- |
| 3883 | no compiler release | 20 stable releases; v1.5.2003 supplemental |
| 3927 | `dxc_2021_07_01`, not v1.5.2003 | 19 SPIR-V-capable stable releases; v1.5.2003 supplemental and unprobeable |
| 6727 | no compiler release | 20 stable releases; v1.5.2003 supplemental |

The captures remain on disk as corroboration but do not change a count,
boundary, or verdict.

### 10. `godbolt-note.txt` is compiled

Promoted to SKILL.md. A banner must describe structural evidence such as an
`OpDecorate` line, signature row, or exit code; it must not contain the token
it says generated output lacks. 3927 and 6727 both now obey that rule.

## Independent verification follow-ups

The post-collation check confirmed that adding `0x80AA001C` and `0x80AA001D`
changed no archived verdict: all eight existing captures with those statuses
already matched the narrow `Internal Compiler error` text marker. It also found
one missing LLVM HRESULT. `INTERNAL_STATUS` now includes:

- `0x80AA001B` (`DXC_E_LLVM_FATAL_ERROR`), whose emitter is
  `report_fatal_error` in `lib/Support/ErrorHandling.cpp`;
- `0x80AA0018` (`DXC_E_GENERAL_INTERNAL_ERROR`), used by internal invariant
  checks in RDAT, subobject, and view-id construction.

Both have status-only regression tests. Two neighbours remain deliberately
excluded, with negative tests:

- `0x80AA0017` (`DXC_E_OPTIMIZATION_FAILED`) is emitted only by DXIL-conversion
  cleanup checks, but the source does not establish that malformed or
  unsupported input cannot reach them.
- `0x80AA0019` (`DXC_E_ABORT_COMPILATION_ERROR`) has no emitter in this tree.

Classifying either code alone without stronger evidence risks turning a clean
diagnosed failure into an invented crash, the more dangerous error direction.

The repeated manual path scan is now `scripts/check_paths.py`, invoked by
`test_predicates.py`. It scans committable text while excluding `.cache/`,
`bin/`, `out/`, and `__pycache__/`, matches ordinary and JSON-escaped
separators, and enforces exact counts for four commented exceptions. Current
result: 16 intentional matches in four files and zero unexpected paths.

## Artifact integrity

Each `expected.md` explicitly records that it was written before execution, and
its issue's first timestamped capture is later. Every predicate states its
control in `match.json`, and the captured controls satisfy their declared
expectations:

| Issue | Predicate controls checked |
| --- | --- |
| 6727 | parse-error, no-divide, and source-embedded-token controls all force `no-match` |
| 2952 | non-RT and compute controls force `no-match`; alternate payload size preserves `match`; field-search self-test is inside the predicate |
| 3362 | equal-pipeline control forces `no-match`; subset-signature control forces `match`, including v1.4.1907 |
| 3883 | initialized-index control compiles cleanly and forces `no-match` |
| 3927 | genuinely unused-resource control forces `no-match`; trivial shader proves old-package backend absence; `-O0` identity control preserves `match` |

The per-issue sections below name the file that decides each verdict. Claims
not directly verified are stated as caveats rather than inferred.

## Per-issue findings

### 6727 — two-output integer operations are not exposed through HLSL

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`enhancement-not-bug`.

Decisive evidence:

- `manual-case-fxc-vs-dxc.txt`: FXC emits one two-output DXBC `udiv`; DXC emits
  separate LLVM `udiv` and `urem`.
- `out-main-debug.txt`: the multiply-high route widens to 64 bits and adds the
  optional 64-bit-integer feature.
- source: DXIL opcodes 41/42/43 use `BinaryWithTwoOuts`;
  `gen_intrin_main.txt` exposes none of them, and the only emitter is the
  DXBC-to-DXIL converter.
- all 20 stable releases compile the probe and show the same absence.

The timeline contains a second DXC request, 4612, already closed into 6727,
and an external LLVM DirectX-backend issue. Neither is one of the previously
triaged 50 issues.

### 2952 — half available, half absent from the shipped API

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`enhancement-not-bug`; **text stale**.

Decisive evidence:

- `out-main-debug-refl2952.txt`: reflection walk completes, the field-search
  self-test passes, shader kinds agree for 7/7 functions, and payload size is
  unavailable through `D3D12_FUNCTION_DESC`.
- `manual-case-release-matrix.txt`: the same result on all 20 stable release
  DLLs; the harness is held fixed while each release DLL varies.
- `manual-case-ground-truth-witnesses.txt`: RDAT contains payload sizes, DXC's
  own dumper prints the shader kind, and release packages do not ship the RDAT
  reader headers.

The function type is encoded in `Version`, but public enum names stop before
the DXIL raytracing kinds. Payload size has been in RDAT since 2018 but has no
supported shipped surface. This is distinct from 3237: that issue has no
parameter records in RDAT at all, while 2952's data exists and needs exposure.

### 3362 — matching configurations produce matching signatures

**Confirmed verdict:** `does-not-repro`, `never-repro'd-in-releases`, high
confidence, `enhancement-not-bug`; **text stale**.

Decisive evidence:

- `attach/pixel_pack_optimized`: embedded command line omits
  `-pack-optimized`.
- `out-main-debug.txt`: matching DS and PS options plus the shared four-element
  struct produce identical signature locations.
- `variant-control-subset-main-debug.txt`: the three-element PS subset produces
  the expected mismatch, proving the predicate can fire.
- `out-v1.4.1907.txt`: automatic retry accepts `-pack_optimized` and produces a
  valid `no-repro`; the positive control also fires on that release.

All 20 stable releases agree. The remaining actionable work is diagnostics,
DXIL documentation, and connected-stage hull/domain coverage, not a packing
regression.

### 3883 — one internal failure, five presentations

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`still-valid-keep-open`.

Decisive evidence:

- `manual-case-signature-census.txt`: five observed failure presentations.
- `manual-case-assert-stack.txt`: Debug reaches
  `TranslateCBGepLegacy` → `getUniqueInteger`; continuing past asserts reaches
  the Release-path `cast<StructType>` failure.
- `variant-control-initialised-main-debug.txt`: initializing the index compiles
  cleanly.
- FXC emits X4000 for both uninitialized spellings.

The worker's status-only prose was corrected. The predicate logic was not
changed.

### 3927 — correct module, incomplete dead-resource elimination

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`enhancement-not-bug`.

Decisive evidence:

- `manual-case-report-fidelity.txt`: the reporter's 64-line module is identical
  to the v1.6.2106 capture.
- `out-main-debug.txt`: Tex0/SS0 bindings survive; Tex1/SS1 are removed.
- `variant-control-unused-main-debug.txt`: genuinely unused declarations are
  removed, proving the predicate discriminates.
- `variant-O0-main-debug.txt`: all four resources survive when optimization is
  disabled, placing the observed elimination in spirv-opt.

The result reproduces on every stable release with a SPIR-V backend. The
v1.4.1907 package is unprobeable, confirmed with a trivial shader.

## Cross-issue consistency

6727 and 2952 are both "capability exists below the public surface" requests
and receive the same disposition: `repros` plus `enhancement-not-bug`. Neither
is treated as fixed merely because the lower-level representation exists.

Neither duplicates a previously triaged issue:

- 6727's duplicate request was closed into 6727 itself and is not in the
  triaged set.
- 2952 is adjacent to 3237 but materially different: 3237 needs new parameter
  data in RDAT; 2952 needs a public route to data already present.

## Prior-batch history re-check

No earlier stable-release verdict or boundary changed.

Finding 9 itself required no prior history re-check: prereleases are outside
formal history unless an issue explicitly opts in, so the earlier concern
about a boundary being hidden at v1.5.2003 was void. Supplemental v1.5.2003
captures made while investigating 3092, 3189, 3251, 3259, 3305, 3377, 3693,
and 3726 remain corroboration only and exposed no contradiction with a stable
boundary.

Findings 2 and 7 did require the originally requested re-check. The known
earlier `Unknown argument` demotion on 3189 was independently resolved by a
flag-free SPIR-V-presence control. The large Unknown-argument population on
8732 was already recorded as unmeasurable, not used as evidence of a fix.
Therefore no prior report required a verdict change.

Residual uncertainty is explicit: `reindex` cannot create missing executions,
and a default binary search does not visit every stable release. Population
counts and exhaustive invalid-probe counts are warranted only where `--linear`
or an explicit release matrix was used.

## Independent draft review

Final review used `claude-sonnet-5`, different from every worker model. 6727
also retained its earlier `gpt-5.6-sol` review.

Applied:

- 3362: corrected the precise legacy spelling statement and reconciled
  `text_stale`.
- 3883: replaced "silent undef" with "unguarded undef".
- 6727: shortened the external LLVM mapping detail.
- 2952: removed speculation about why the request read as unsupported.

Rejected: no whole paragraph was removed from 3362 or 3927; the reviewer found
their remaining detail necessary to the constructive disposition and the
source-of-fix claim. Every `verdict.json` now has a non-empty `reviewed_by`
whose model differs from `triaged_by`.

## What this batch taught about the method

1. **Never let an unexecuted release become evidence.** Retry legacy option
   spellings, require per-release controls, count trimmed invalid probes, and
   stop binary search on an unprobeable interior point.
2. **Stable-release policy must be represented in tooling.** Prereleases are
   named but excluded; the narrow exception requires both explicit naming in
   the issue and a persistent `release-policy.json` opt-in.
3. **A harness is not dxc.** Bisection must hard-error rather than silently
   substituting the wrong executable.
4. **Absence and presence both need in-predicate self-tests.** Prose controls
   decay; predicate clauses are rechecked by every `reindex`.
5. **Read attached output before reconstructing it.** Embedded command lines
   can decide the issue more strongly than an agent approximation.
6. **Internal failure is a classification, not one status code.** Status plus
   a narrow, build-agnostic marker can preserve one defect across changing
   presentations without matching ordinary diagnostics.
7. **Compiler Explorer notes are program input.** Treat every banner token as
   something the compiler may echo into output.
8. **Timeline reads aid both provenance and duplicate checks.** Include the
   source repository so an external issue is not mistaken for a local one.
9. **Commit messages are a publishing surface.** Issue references create
   permanent timeline events; use bare numbers and never rewrite history to
   try to retract them.
10. **Date symbols repository-wide before scoping by path.** File moves made a
    path-scoped `git log -S` date 2952's RDAT field two months late; the
    repository-wide history found its real February 2018 introduction.
11. **A recurring clean-up gate belongs in code.** Exact-count allowlists and
    positive regex controls turn path exceptions into checked policy rather
    than a judgement call repeated every batch.

## Verification

- Predicate/tool regression tests: pass.
- Final reindex: 55 issues / 950 runs; no changed verdicts, stale captures,
  evidence gaps, or control failures.
- `triage.py audit`: pass for all 55 issues.
- Git status: zero changes outside this skill.
- `check_paths.py`: pass; 16 documented matches in four allowlisted files,
  zero unexpected paths.
- Staging dry run: zero binary candidates; index contains zero staged files.
- Reviewer audit: every verdict has `reviewed_by`, with a different model from
  its author.
- Public-citation audit: no unreconciled fork-local SHA in a draft, verdict, or
  batch report.
- GitHub timeline checks: no triage-created events for any batch-011 issue.
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


### Draft — [#2952](https://github.com/microsoft/DirectXShaderCompiler/issues/2952) Expose ray payload size / function type through Reflection

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2952](https://github.com/microsoft/DirectXShaderCompiler/issues/2952).

Still open on `main` (13730886e), and the answer to the 2024 question in this
thread is "half of it already works, and the other half is closer than it
looks".

**The function type is already available.** `CFunctionReflection::GetDesc` sets
`D3D12_FUNCTION_DESC.Version` from `DxilFunctionProps::shaderKind`
([`DxilContainerReflection.cpp:2848`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/DxilContainerReflection.cpp#L2848)),
so `D3D12_SHVER_GET_TYPE(Version)` returns the raytracing shader kind. On a
library with one entry of every DXR 1.0 kind it gives 7/8/9/10/11/12 for
raygeneration / intersection / anyhit / closesthit / miss / callable and 6 for a
plain export — correct for all seven functions, on every release from v1.4.1907
to v1.9.2607 in the 20-stable-release matrix. `dxa -dumpreflection` already
prints it as `Shader Version: AnyHit 6.3`.

The catch is that `d3d12shader.h` defines `D3D12_SHADER_VERSION_TYPE` only up to
5. Values 6–15 are `hlsl::DXIL::ShaderKind`, which ships in no public header —
DXC's own dumper casts to the internal enum to print them
([`D3DReflectionDumper.cpp:160`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/DxilContainer/D3DReflectionDumper.cpp#L160)).
Callers can get the right answer only by hardcoding constants they were never
given.

**The payload size is in the container, but no shipped DXC header exposes a
supported reader.**
`RuntimeDataFunctionInfo` carries `PayloadSizeInBytes` and
`AttributeSizeInBytes`
([`RDAT_LibraryTypes.inl:205`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/include/dxc/DxilContainer/RDAT_LibraryTypes.inl#L205)),
present since 0a098d7cb (2018-02) — before this issue was filed. It is in the DXIL
too, as `dx.entryPoints` entry-property tags 6 and 7. But `D3D12_FUNCTION_DESC`
has no field that could hold it: enumerating all 31 numeric fields and searching
them for the size the container reports finds nothing, on every stable release
tested.
And `DxilRuntimeReflection.h` / `RDAT_*.inl` are not in any release package —
`inc/` ships `d3d12shader.h`, `dxcapi.h`, and latterly `dxcerrors.h`,
`dxcisense.h`, `dxcpix.h`. An application can pull the raw bytes with
`IDxcContainerReflection::GetPartContent(DFCC_RuntimeData)` and then has no
supported way to parse them.

So this is an API-surface request, not a data-capture one — the data has been
recorded since 2018. The options are roughly: add fields to
`D3D12_FUNCTION_DESC` (declared in DirectX-Headers, so not DXC's alone to
change), add a DXC-specific reflection interface, or ship the RDAT reader. That
is a design call for the team.

Method: `dxc.exe` cannot express a reflection query, so this was measured with a
small harness driving `IDxcContainerReflection` → `ID3D12LibraryReflection` →
`ID3D12FunctionReflection` against each release's own `dxcompiler.dll`. A
control library with no raytracing entries scores no-match on every release, so
"the API reported nothing" is not being satisfied vacuously.

[Compiler Explorer](https://godbolt.org/z/YT1q1cqjb) shows the payload size and
shader kind sitting in `dx.entryPoints` on both `dxc_1_6_2112` and trunk; it
cannot show the reflection API.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
````

### Draft — [#3362](https://github.com/microsoft/DirectXShaderCompiler/issues/3362) pack-optimized issue with domain shader

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3362](https://github.com/microsoft/DirectXShaderCompiler/issues/3362).

The actionable gap here appears to be diagnostics and documentation:
`-pack-optimized` silently assumes that connected stages use the same option and an identical
interstage signature.

The attached disassemblies record the command line that produced each one. The domain-shader
dump includes `-pack-optimized`; the pixel-shader dump named `pixel_pack_optimized` does not.
The two quoted tables were therefore produced under different packing rules.

Rebuilding the shaders from the struct in the report, with the flag on **both** stages, the two
signatures come out identical on `main` (`13730886e`):

```
ds_6_0  -pack-optimized     Output signature:
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; PREVIOUSPOSITION         0   xyzw        0     NONE   float   xyzw
; SV_Position              0   xyzw        1      POS   float   xyzw
; SV_ClipDistance          0      w        2  CLIPDST   float      w
; NORMAL                   0   xyz         2     NONE   float   xyz

ps_6_0  -pack-optimized     Input signature:
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; PREVIOUSPOSITION         0   xyzw        0     NONE   float   xyzw
; SV_Position              0   xyzw        1      POS   float
; SV_ClipDistance          0      w        2  CLIPDST   float      w
; NORMAL                   0   xyz         2     NONE   float   xyz
```

Compiler Explorer, three panes over one source: <https://godbolt.org/z/a1hKP6Tvs> — panes 1 and
2 are the DS and the PS with the flag (`SV_ClipDistance` at register 2, mask `w` in both, on two
compiler versions years apart); pane 3 is the same PS without the flag, and it is the table
quoted in this issue.

A whole `VS → HS → DS → PS` pipeline built the same way also agrees at every stage, including
the patch-constant signature, so nothing here is specific to domain shaders. The same holds on
all 20 stable releases back to v1.4.1907 (2019-07) — there is no regression to bisect. (That
release rejects `-pack-optimized` but accepts `-pack_optimized` and `/pack-optimized`.)

Two conditions have to hold, and the second is easy to miss:

1. **Pass `-pack-optimized` to every stage in the PSO**, not just one.
2. **The interstage signature must be identical**, not merely compatible. The pixel-shader table
   in the report has three elements where the domain shader emits four (no `NORMAL`). Optimized
   packing is a global optimisation over the whole element list, so removing one element moves
   the others: with the flag on both stages, the 4-element DS gives `SV_ClipDistance` register 2
   mask `w` while a 3-element PS gives register 2 mask `x`. This is what
   *"assuming identical signature provided for each connecting stage"* in the flag's help text
   is asking for. Unused interstage members must still be declared in the consuming stage's
   input struct — which is what sharing the struct through a header is meant to guarantee.

DXC gives no diagnostic when either condition is broken; the failure surfaces only at
`CreateGraphicsPipelineState`, as it did here. Whether it should is a design decision for the
maintainers. Two smaller gaps back it up: for DXIL the flag's contract exists only as the
one-line `--help` string (`docs/SPIR-V.rst` documents the SPIR-V behaviour), and the three
`pack_optimized` regression tests are all `vs_6_0`, single stage, with no test that two
connected stages agree.

I did not rerun D3D12 PSO creation; the compiler-verifiable result is that matching options and
matching structs produce matching signatures. The remaining work is therefore a diagnostic, a
documented contract, or connected-stage hull/domain test coverage. That evidence supports
reclassifying this from `bug` to `usability`/`docs`/`diagnostic`, subject to maintainer context.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3883](https://github.com/microsoft/DirectXShaderCompiler/issues/3883) DXC Compiler Crash

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3883](https://github.com/microsoft/DirectXShaderCompiler/issues/3883).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and it has never worked:
`bisect --linear` scores all 20 stable release binaries from v1.4.1907 (2019-07)
through v1.9.2607 (2026-07), plus a clean Debug build of `main`, as internal
failures.

```
$ dxc -T ps_6_0 -E PSMain repro.hlsl        # Debug main
Internal compiler error: LLVM Assert        # exit 0xE0000001

Error: assert(this->getType()->isVectorTy() && "Only valid for vectors!")
File:  lib/IR/Constants.cpp(1419)
    llvm::Constant::getSplatValue
    llvm::Constant::getUniqueInteger
    `anonymous namespace'::TranslateCBGepLegacy
    `anonymous namespace'::TranslateCBAddressUserLegacy
    `anonymous namespace'::TranslateCBOperationsLegacy
```

`TranslateCBGepLegacy` (`lib/HLSL/HLOperationLower.cpp:8871`) tests the cbuffer index with
`dyn_cast<Constant>` and then calls `getUniqueInteger()` on it. `UndefValue` *is* a
`Constant`, so the undefined index goes straight through. Under `NDEBUG` the asserts are
compiled out and the value reaches `getAggregateElement(0U)` →
`UndefValue::getNumElements()` → `Type::getStructNumElements()`, which is a bare
`cast<StructType>` on an `i32` and throws `DXC_E_LLVM_CAST_ERROR`. That is the release
symptom, reproducible from the same Debug binary by continuing past both asserts under a
debugger.

**Two things worth adding to the report.**

1. **The self-initialisation is not the trigger.** Plain `uint index; return colors[index];`
   fails identically, and the only thing it prints is the internal cast failure — no
   `-Wuninitialized` warning, nothing pointing at the variable. That warning fires only on the
   `index = index` spelling, and it has never stopped codegen. The same undefined index
   outside the cbuffer path (a `Buffer<float4>`) compiles at exit 0 and emits
   `bufferLoad(..., i32 undef, i32 undef)`. So this input is either an internal failure or an
   unguarded `undef` in the DXIL, and never an error.

2. **FXC already diagnoses it**, on both spellings:
   `error X4000: variable 'index' used without having been completely initialized`. The
   initialised form compiles cleanly under FXC, so that is the diagnostic and not a general
   FXC objection to the shader.

Compiler Explorer, FXC beside DXC 1.6.2112 and trunk: https://godbolt.org/z/6c9h3r4a3

The same defect has had five presentations without ever being fixed: an access violation
with empty stderr; an access violation with a message; `0x80AA001D`; plain `E_FAIL` plus the
build-agnostic `cast<X>() argument` marker; and the Debug LLVM assert above. Worth knowing
before reading any old "does this still repro?" note: the current spelling looks like an
ordinary compile error, and CE's Linux builds print `cast<X>()` where Windows prints
`llvm::cast<X>()`.

Suggested labels: add `fxc-disagrees` (measured above) and `diagnostic` (the ask is a
diagnostic in place of an internal failure). Existing labels all look right.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3927](https://github.com/microsoft/DirectXShaderCompiler/issues/3927) [SPIR-V] Not all unnecessary bindings are eliminated using SPIR-V backend

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3927](https://github.com/microsoft/DirectXShaderCompiler/issues/3927).

Still reproduces on `main` (1.9.0.5433, `13730886e`), unchanged.

The shader in the report compiles to the same four lines it did in 2021:

```
OpDecorate %Tex0 DescriptorSet 0
OpDecorate %Tex0 Binding 0
OpDecorate %SS0 DescriptorSet 0
OpDecorate %SS0 Binding 1
```

`%Tex1`/`%SS1` are gone, as reported. `%Tex0`/`%SS0` stay because the sampled value feeds the
`if` condition, and the branch is not folded even though both of its targets end in `OpKill`.

**Compiler Explorer:** https://godbolt.org/z/eqxrve7j7 — `dxc_1_6_2112` and `dxc_trunk`. The
two modules differ (the older one still evaluates `&&` eagerly), but both keep the two
bindings.

**History.** A linear scan of all 20 stable releases from v1.4.1907 to v1.9.2607 reproduces
it in the 19 that have a SPIR-V backend, i.e. everything from v1.5.2010 onward. v1.4.1907 is
not evidence either way: it answers `SPIR-V CodeGen not available` even for a trivial pixel
shader.

Two details from re-running it that may be worth having on the thread:

- The repro reproduces the reporter's module *exactly* — the disassembly quoted in the issue
  body matches this triage's v1.6.2106 capture (`dxc_2021_07_01`) line for line, all 64 lines.
- Compiled with `-O0`, all four resources keep bindings. So every elimination visible here is
  spirv-opt's, none of it the SPIR-V emitter's — consistent with the 2024-08-22 comment
  placing a fix in spirv-opt. `SpirvEmitter::spirvToolsOptimize` registers
  `RegisterPerformancePasses` and nothing issue-specific, so DXC-side changes would not be
  involved. Of the `-fspv-*` and `-fvk-*` flags, the only binding-related one points the other
  way: `-fspv-preserve-bindings` keeps *more* bindings. There is no flag asking for more
  aggressive elimination.

**Labels:** the issue is still only `spirv`. Suggest adding `enhancement` (the module is
correct, just not minimal — nothing miscompiles) and `up-for-grabs`, which is what the
2024-08-22 comment already says in prose. I may be missing context from outside this thread.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#6727](https://github.com/microsoft/DirectXShaderCompiler/issues/6727) Support IMul/UMul/UDiv with two outputs from HLSL

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6727](https://github.com/microsoft/DirectXShaderCompiler/issues/6727).

Still absent on `main` at
[13730886e](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e6a9019e4e0823746470f3ab75341d6b)
(the Debug build used here self-reports a fork-local commit, but its compiler
source is identical to that one).

**What HLSL produces today.** In `cs_6_0`, the high half of a 32x32 multiply is
reachable only by widening to `uint64_t`, which adds the optional `64-Bit
integer` feature to the shader, and quotient and remainder of one operand pair
stay separate:

```llvm
;       64-Bit integer
  %8 = mul nuw i64 %7, %6
  %9 = lshr i64 %8, 32
  %10 = trunc i64 %9 to i32
  %11 = trunc i64 %8 to i32
  %12 = udiv i32 %4, %5
  %13 = urem i32 %4, %5
```

**FXC emits the two-output DXBC operations from the same source.** For `a / b`
and `a % b`, `fxc /T cs_5_0` emits one `udiv r0.x, r1.x, r0.x, r0.y`, quotient
and remainder being its two outputs. For a plain `a * b` it emits
`imul null, r1.y, r0.y, r0.x` — DXBC's multiply has two destinations and the
high one is discarded into `null`. The divide/remainder pair side by side on
Compiler Explorer: https://godbolt.org/z/1nG4f73d3

**The opcodes are present — just not reachable from HLSL.** `IMul` = 41,
`UMul` = 42, `UDiv` = 43, op class `BinaryWithTwoOuts`, `dx.op` name
`binaryWithTwoOuts`, returning a two-`i32` struct
(`include/dxc/DXIL/DxilConstants.h`, `lib/DXIL/DxilOperations.cpp`,
`docs/DXIL.rst`). The only emitter in the tree is the DXBC-to-DXIL converter
(`projects/dxilconv/lib/DxbcConverter/DxbcConverter.cpp:2651-2657`), matching
tex3d's note that the shader5x HLK coverage arrives through translation.
`utils/hct/gen_intrin_main.txt` has no entry for any of them.

Worth knowing before implementing: `lib/HLSL/HLOperationLower.cpp:7860` reads
`{IntrinsicOp::IOP_umul, TranslateMul, DXIL::OpCode::UMul}`, but `IOP_umul` is
the unsigned overload of `mul()` and `TranslateMul` never reads its `opcode`
parameter, so that entry emits nothing.

The SPIR-V path has the same gap: `-spirv` on the same shader gives
`OpCapability Int64` with a 64-bit `OpIMul`, and separate `OpUDiv`/`OpUMod` —
no `OpUMulExtended`, the instruction behind GLSL's `umulExtended`.

**History.** All 20 stable release binaries from v1.4.1907 (2019-07) through
v1.9.2607 compile the shader and none emits the op, so this is not a
regression.

**Related work elsewhere.** LLVM's DirectX backend tracks lowering these ops in
[llvm/llvm-project#128638](https://github.com/llvm/llvm-project/issues/128638)
(open since 2025-02), proposing overflow-intrinsic lowering and explicitly
waiting on the HLSL-side decision here. Searching `microsoft/hlsl-specs` issues
and PRs for these operations returns no results.

**Label suggestion:** add `fxc-disagrees`. `enhancement` and `high-impact` still
fit.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
````

---

## Caveats

- 2952's Compiler Explorer link proves the data exists, not that a reflection
  API exposes it. The API result comes from the fixed harness.
- 3362's runtime PSO creation failure was not rerun; signature agreement and
  the attachment command lines were verified.
- 3927 establishes optimization ownership and a missing optimization, not
  incorrect SPIR-V semantics.
- Supplemental prerelease probes are evidence files, not part of stable-release
  history under the current policy.
