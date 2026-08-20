# DXC issue triage — batch 019

**Ground truth:** local Debug compiler `main-debug`, registered at public commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df).
The binary self-reports `1.9.0.5465 (triage, 7665270b9)` — a fork-local commit id that
resolves for nobody else — so the citation above is the public upstream commit the source
corresponds to, not what `--version` prints. Equivalence was proven by tree, not by hash:
`git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` reports nothing
outside `.github/skills/dxc-issue-triage/`, while the same query against an older commit
(the required control) reports real source/test/doc changes, so the query is capable of
detecting a difference and the empty result is a genuine equivalence rather than a query that
cannot see anything. This exact check, repeated per issue, is what backs every "still
reproduces on `main`" claim below.

No DXC source was modified by this batch. **Nothing was posted, edited, labelled, closed,
reacted to, or referenced-by-commit-message on GitHub.** This report is itself a fresh
collation session, briefed only by what is on disk in `data/issues/<nnnn>/` for the 100 issue
numbers below (queried from `triage.db`/`verdict.json`, not guessed or taken from any prior
session's summary) plus the specific external artifacts named in this batch's brief
(gpt-5.3-codex's four step-10 review logs and the existing-issue refresh snapshots).

> [!IMPORTANT]
> **Sampling bias.** This batch is the 100 oldest *previously-untriaged* open issues
> (#4766–#6084), selected purely by filing date. That is a single, contiguous age slice —
> every issue was filed between **2022-11-04 and 2023-11-30** — not a representative sample of
> the current backlog. Verdicts here describe DXC's behaviour across roughly twenty stable
> releases spanning that slice's whole subsequent history; they say nothing about how the
> *current* backlog (2024–2026 filings) looks, and the batch's category mix (see below) is
> whatever this age band happened to contain, not a deliberate mix of crash/spirv/mid-age
> issues.

## Headline

- **100 issues, 100 verdicts, all high-or-medium confidence, zero left unresolved.**
  69 `repros`, 9 `does-not-repro`, 4 `changed-behavior`, 17 `not-compiler-verifiable`,
  1 `inconclusive`. Suggested actions: 71 `still-valid-keep-open`, 13 `needs-human-judgement`,
  **7 `close-fixed`**, 6 `enhancement-not-bug`, 2 `needs-repro-from-reporter`,
  1 `duplicate-of #8001`.
- **7 close-fixed issues** (#4965, #5080, #5261, #5563, #5587, #5681, #5748), every one checked
  against every probeable stable release back to its own bisection floor (v1.4.1907 for two of
  them; a later floor for the other five, where an older release genuinely cannot express the
  feature under test — see each issue's own entry below), with a Compiler Explorer link
  corroborating both ends, and an explicit "strong, not certain" flag on any commit-level
  attribution none of them built to confirm. All seven were independently checked against their
  raw evidence by gpt-5.3-codex; see **Blind checks** below for exactly what that means per
  issue and where the trail on disk stops.
- **A serious, previously-undocumented tooling hazard was found and fixed this batch:** the
  ordinary (non-spelling-retry) `run`/`bisect` probe path shared one issue directory's scratch
  seed across an entire release sweep, so a release whose own multi-line pipeline failed partway
  could silently disassemble a *different* release's leftover output and score a reproduction
  that never happened. Caught on **#5704**, independently confirmed by re-deriving the corrected
  history through an isolated per-release matrix, and closed in `triage.py` this session — see
  **The #5704 stale-output-file hazard**.
- **Two workers independently misdated the same synthetic commit** (`8a8b29f96`) as a symbol's
  "introduction" via `git log --all -S` (#5172, #5436) — a second, independent trap this
  checkout's shallow-clone/multi-remote history invites, on top of the tooling hazard above. Both
  are now documented in `SKILL.md` with a required `merge-base --is-ancestor` check.
- **9 issues carry `text_stale`**; four (#5059, #5704, #5823, #5985) describe a defect whose
  *reported* symptom shape changed while the underlying defect is still fully live — the exact
  failure mode this field exists to catch, since a naive spot-check of the literal wording would
  misread each as fixed.
- **Cross-issue triangulation:** three independently-triaged issues (#5269, #5668, #5686) all
  converge on the *same* one-line validator bug in `ValidateAsIntrinsics`; two more (#5261,
  #5681) independently attribute their fixes to the *same* commit window and PR. See
  **Cross-issue analysis**.
- **Existing-issue refresh:** 107 pre-batch-019 issues were re-fetched (metadata/comments only,
  no compiler reruns); 4 changed in a way worth a maintainer's attention (#3150, #7033, #8732,
  #8737), 3 more show Unicode-normalization-only differences. No compiler measurement was
  refreshed for any of the 107. See **Existing-issue refresh**.
- Every one of the 100 batch issues' GitHub timelines was fetched read-only; **zero
  cross-reference events were created by this triage**, on any issue, in this or any prior
  batch-019 session. See **Timeline check**.
- Every `summary`/`text_stale` field was re-read against its issue's `notes.md`, sentence by
  sentence (two independent full passes plus my own verification of every flagged concern), and
  every `match*.json` predicate's `note` was re-checked against its actual `kind`/`value`
  structure (88 files). No unresolved discrepancy remains in either audit; see the two dedicated
  sections below for what was flagged and how each resolved.

## Verdict counts

| status | count |  | suggested action | count |
| --- | --- | --- | --- | --- |
| repros | 69 |  | still-valid-keep-open | 71 |
| not-compiler-verifiable | 17 |  | needs-human-judgement | 13 |
| does-not-repro | 9 |  | close-fixed | 7 |
| changed-behavior | 4 |  | enhancement-not-bug | 6 |
| inconclusive | 1 |  | needs-repro-from-reporter | 2 |
|  |  |  | duplicate-of #8001 | 1 |

repro quality: 67 complete, 16 agent-constructed, 9 prose-only, 5 partial, 3 none. Confidence:
96 high, 4 medium (all four are `not-compiler-verifiable`/`inconclusive` issues where the
lower confidence is about the underlying claim, not about the measurement: #5309, #5476,
#5848, #6003). 59 issues got a Compiler Explorer link; the other 41 have a recorded,
issue-specific reason `godbolt` cannot show anything (a linker step, a COM API, a build/CI
question, a platform-specific locale bug, and similar — CE's single-pane, single-`dxc.exe`
model cannot express any of them).

## Summary table

Verdict/action/CE-link per issue, oldest first. `[stale]` marks the 9 issues carrying
`text_stale`; see that section for what is stale and why.

| # | Title | Verdict | Action | CE |
| --- | --- | --- | --- | --- |
| [4766](https://github.com/microsoft/DirectXShaderCompiler/issues/4766) | Build dxil/dxcompiler as a static library? | not-compiler-verifiable | needs-human-judgement | skipped |
| [4786](https://github.com/microsoft/DirectXShaderCompiler/issues/4786) | DxbcConverter can corrupt integer ICB values (x86) | repros | still-valid-keep-open | skipped |
| [4792](https://github.com/microsoft/DirectXShaderCompiler/issues/4792) | libdxcompiler.so locks up under many threads | repros | still-valid-keep-open | skipped |
| [4805](https://github.com/microsoft/DirectXShaderCompiler/issues/4805) | Custom include handler ignored with -Zi [stale] | changed-behavior | still-valid-keep-open | skipped |
| [4858](https://github.com/microsoft/DirectXShaderCompiler/issues/4858) | Illegal code motion for CalculateLevelOfDetailUnclamped | repros | still-valid-keep-open | [link](https://godbolt.org/z/1h4fff5Ef) |
| [4871](https://github.com/microsoft/DirectXShaderCompiler/issues/4871) | inout pre-decrement subtracts 2, not 1 [stale] | repros | still-valid-keep-open | [link](https://godbolt.org/z/4318d6hbY) |
| [4888](https://github.com/microsoft/DirectXShaderCompiler/issues/4888) | Dynamic resources: "All metadata must be used by dxil" [stale] | repros | still-valid-keep-open | [link](https://godbolt.org/z/fhjbK7r4x) |
| [4914](https://github.com/microsoft/DirectXShaderCompiler/issues/4914) | Copying "this" fails (aggregate expr) | repros | still-valid-keep-open | [link](https://godbolt.org/z/jbqesq9P1) |
| [4958](https://github.com/microsoft/DirectXShaderCompiler/issues/4958) | Hull shader with unused globals crashes | repros | still-valid-keep-open | [link](https://godbolt.org/z/zdcvTzcd7) |
| [4965](https://github.com/microsoft/DirectXShaderCompiler/issues/4965) | int f(int) as /E: access violation | does-not-repro | **close-fixed** | [link](https://godbolt.org/z/ee6xoP8jz) |
| [5039](https://github.com/microsoft/DirectXShaderCompiler/issues/5039) | Nonsensical error for undef structured-buffer offset | repros | still-valid-keep-open | [link](https://godbolt.org/z/aM54EnbzT) |
| [5040](https://github.com/microsoft/DirectXShaderCompiler/issues/5040) | Undefined value allowed for buffer load index | repros | still-valid-keep-open | [link](https://godbolt.org/z/cP8cW1v3x) |
| [5059](https://github.com/microsoft/DirectXShaderCompiler/issues/5059) | Loop optimization yields unsupported i33 type [stale] | changed-behavior | still-valid-keep-open | [link](https://godbolt.org/z/PGGE6r8s9) |
| [5064](https://github.com/microsoft/DirectXShaderCompiler/issues/5064) | Improve DXIL validator testing infrastructure | not-compiler-verifiable | needs-human-judgement | skipped |
| [5072](https://github.com/microsoft/DirectXShaderCompiler/issues/5072) | -Fh invalid identifier for library targets | repros | still-valid-keep-open | skipped |
| [5079](https://github.com/microsoft/DirectXShaderCompiler/issues/5079) | Conflict with DirectX-Headers | repros | needs-human-judgement | skipped |
| [5080](https://github.com/microsoft/DirectXShaderCompiler/issues/5080) | cbuffer assert with -fspv-debug=vulkan-with-source | does-not-repro | **close-fixed** | [link](https://godbolt.org/z/9rshx68rz) |
| [5105](https://github.com/microsoft/DirectXShaderCompiler/issues/5105) | Allow unused registers in reflection | repros | still-valid-keep-open | [link](https://godbolt.org/z/snfK4ebdG) |
| [5115](https://github.com/microsoft/DirectXShaderCompiler/issues/5115) | signed/unsigned overload resolution unjustified | repros | still-valid-keep-open | [link](https://godbolt.org/z/xPz8ndv7T) |
| [5116](https://github.com/microsoft/DirectXShaderCompiler/issues/5116) | Weird behavior returning a texture (cs_6_6 vs cs_6_5) | repros | still-valid-keep-open | [link](https://godbolt.org/z/eE8co66vG) |
| [5117](https://github.com/microsoft/DirectXShaderCompiler/issues/5117) | -MD/-MF swallows Sema diagnostics, reports success | repros | still-valid-keep-open | [link](https://godbolt.org/z/s4Mcsxj66) |
| [5165](https://github.com/microsoft/DirectXShaderCompiler/issues/5165) | 8-case switch: "I8 can only used as immediate value" | repros | still-valid-keep-open | [link](https://godbolt.org/z/qPfqjxxnY) |
| [5169](https://github.com/microsoft/DirectXShaderCompiler/issues/5169) | Add D3D_SVC_BIT_FIELD to D3D_SHADER_VARIABLE_CLASS | not-compiler-verifiable | still-valid-keep-open | skipped |
| [5172](https://github.com/microsoft/DirectXShaderCompiler/issues/5172) | IDxcIndex::ParseTranslationUnit ignores IDxcIncludeHandler | repros | enhancement-not-bug | skipped |
| [5173](https://github.com/microsoft/DirectXShaderCompiler/issues/5173) | IDxcCursor misses semantics | repros | enhancement-not-bug | skipped |
| [5175](https://github.com/microsoft/DirectXShaderCompiler/issues/5175) | IDxcCursor: no template parameter/argument querying | repros | enhancement-not-bug | skipped |
| [5184](https://github.com/microsoft/DirectXShaderCompiler/issues/5184) | WaveMatch with a vector input value | repros | still-valid-keep-open | [link](https://godbolt.org/z/GjKe8bn5b) |
| [5194](https://github.com/microsoft/DirectXShaderCompiler/issues/5194) | Can't template an operator() overload | repros | still-valid-keep-open | [link](https://godbolt.org/z/9ajqv56xK) |
| [5244](https://github.com/microsoft/DirectXShaderCompiler/issues/5244) | [SPIR-V] Add RWTexture2DMS support (SM6.7) | repros | still-valid-keep-open | [link](https://godbolt.org/z/oj91s731v) |
| [5255](https://github.com/microsoft/DirectXShaderCompiler/issues/5255) | Rewriter drops a struct still named by a cbuffer | repros | still-valid-keep-open | skipped |
| [5258](https://github.com/microsoft/DirectXShaderCompiler/issues/5258) | FlattenedTypeIterator mishandles bit fields (3 examples) | repros | still-valid-keep-open | [link](https://godbolt.org/z/b9vP5dhMK) |
| [5261](https://github.com/microsoft/DirectXShaderCompiler/issues/5261) | Deadlock loading RayDesc from ByteAddressBuffer | does-not-repro | **close-fixed** | [link](https://godbolt.org/z/1K9zo9Mnc) |
| [5268](https://github.com/microsoft/DirectXShaderCompiler/issues/5268) | Rewriter drops a global a kept global's initializer needs | repros | still-valid-keep-open | skipped |
| [5269](https://github.com/microsoft/DirectXShaderCompiler/issues/5269) | Amplification shader: support empty payload | repros | still-valid-keep-open | [link](https://godbolt.org/z/WfqfzrK91) |
| [5290](https://github.com/microsoft/DirectXShaderCompiler/issues/5290) | Rewriter drops entry param's own type | repros | still-valid-keep-open | skipped |
| [5292](https://github.com/microsoft/DirectXShaderCompiler/issues/5292) | Rewriter keeps a typedef aliasing a removed struct | repros | still-valid-keep-open | skipped |
| [5302](https://github.com/microsoft/DirectXShaderCompiler/issues/5302) | Waterfall loop miscompiled in VS (dx.break stage gap) | repros | still-valid-keep-open | [link](https://godbolt.org/z/jj8fzqMTK) |
| [5309](https://github.com/microsoft/DirectXShaderCompiler/issues/5309) | Dxbc-to-Dxil conversion failure (0x8007007E) | not-compiler-verifiable | needs-repro-from-reporter | skipped |
| [5328](https://github.com/microsoft/DirectXShaderCompiler/issues/5328) | Typo/null-deref risk in HLMatrixBitcastLowerPass.cpp | repros | still-valid-keep-open | skipped |
| [5338](https://github.com/microsoft/DirectXShaderCompiler/issues/5338) | Array-cast crash; FXC constant-folds it | repros | still-valid-keep-open | [link](https://godbolt.org/z/5nqjfhfve) |
| [5350](https://github.com/microsoft/DirectXShaderCompiler/issues/5350) | SM6.8 Work Graph node reflection request | not-compiler-verifiable | needs-human-judgement | skipped |
| [5357](https://github.com/microsoft/DirectXShaderCompiler/issues/5357) | Missing type annotation crashes node record chaining | repros | still-valid-keep-open | [link](https://godbolt.org/z/eqjMv4v5Y) |
| [5389](https://github.com/microsoft/DirectXShaderCompiler/issues/5389) | Bare-literal swizzle `as*` cast: invalid bitcode | repros | still-valid-keep-open | [link](https://godbolt.org/z/Y45Yhd3P5) |
| [5395](https://github.com/microsoft/DirectXShaderCompiler/issues/5395) | No shadow warning for HV2021 loop variable | repros | enhancement-not-bug | [link](https://godbolt.org/z/KzYb6cKTE) |
| [5416](https://github.com/microsoft/DirectXShaderCompiler/issues/5416) | depfile generation excludes normal compilation | repros | still-valid-keep-open | [link](https://godbolt.org/z/3jn1eM9K4) |
| [5417](https://github.com/microsoft/DirectXShaderCompiler/issues/5417) | GetAttributeAtVertex reads not counted as "Used" | repros | still-valid-keep-open | [link](https://godbolt.org/z/zWTG5Wrxv) |
| [5423](https://github.com/microsoft/DirectXShaderCompiler/issues/5423) | dxr.exe ignores -D macro definitions | repros | still-valid-keep-open | [link](https://godbolt.org/z/GzETMvxvs) |
| [5434](https://github.com/microsoft/DirectXShaderCompiler/issues/5434) | Add validation for Annotate*Handle intrinsics | repros | still-valid-keep-open | skipped |
| [5436](https://github.com/microsoft/DirectXShaderCompiler/issues/5436) | Add assert for unvalidated dxil opcodes | not-compiler-verifiable | still-valid-keep-open | skipped |
| [5448](https://github.com/microsoft/DirectXShaderCompiler/issues/5448) | Organize GetResourceFromHandle/GetResourceFromVal usage | repros | enhancement-not-bug | skipped |
| [5476](https://github.com/microsoft/DirectXShaderCompiler/issues/5476) | [macOS] dxc -fcgl + root signature dumps nothing | not-compiler-verifiable | needs-human-judgement | [link](https://godbolt.org/z/vajbo9sxW) |
| [5481](https://github.com/microsoft/DirectXShaderCompiler/issues/5481) | Enable clang source-based code coverage on Windows | not-compiler-verifiable | still-valid-keep-open | skipped |
| [5491](https://github.com/microsoft/DirectXShaderCompiler/issues/5491) | Unused wave intrinsic call not eliminated | repros | still-valid-keep-open | [link](https://godbolt.org/z/1T6e4zWsf) |
| [5546](https://github.com/microsoft/DirectXShaderCompiler/issues/5546) | Docs: clarify discard is not control flow | not-compiler-verifiable | needs-human-judgement | [link](https://godbolt.org/z/rnEKhGWcY) |
| [5554](https://github.com/microsoft/DirectXShaderCompiler/issues/5554) | C++11 enums don't work as integer constants | repros | still-valid-keep-open | [link](https://godbolt.org/z/bqbP386nM) |
| [5563](https://github.com/microsoft/DirectXShaderCompiler/issues/5563) | "found unregistered decl": partial template spec. (SPIR-V) [stale] | does-not-repro | **close-fixed** | [link](https://godbolt.org/z/Y1W7q714v) |
| [5567](https://github.com/microsoft/DirectXShaderCompiler/issues/5567) | -Wcomma-in-init could be more aggressive | repros | still-valid-keep-open | [link](https://godbolt.org/z/dPM8vnz5b) |
| [5573](https://github.com/microsoft/DirectXShaderCompiler/issues/5573) | "External declaration is unused" after resource assignment | repros | still-valid-keep-open | [link](https://godbolt.org/z/r6TGKo7sv) |
| [5587](https://github.com/microsoft/DirectXShaderCompiler/issues/5587) | Bitfield initialization order dependence | does-not-repro | **close-fixed** | [link](https://godbolt.org/z/xG8Kj4v58) |
| [5595](https://github.com/microsoft/DirectXShaderCompiler/issues/5595) | Support hash-stability test in lit | not-compiler-verifiable | still-valid-keep-open | skipped |
| [5632](https://github.com/microsoft/DirectXShaderCompiler/issues/5632) | Construct-cast array-to-non-array: DXIL crash | repros | still-valid-keep-open | [link](https://godbolt.org/z/W9Kr6fvPa) |
| [5633](https://github.com/microsoft/DirectXShaderCompiler/issues/5633) | No warning for statically-checkable out-of-bounds index | repros | still-valid-keep-open | [link](https://godbolt.org/z/KG9b5j1f8) |
| [5668](https://github.com/microsoft/DirectXShaderCompiler/issues/5668) | DispatchMesh fails on empty struct payload | repros | still-valid-keep-open | [link](https://godbolt.org/z/rqTqed5s8) |
| [5674](https://github.com/microsoft/DirectXShaderCompiler/issues/5674) | Crash when `matrix` used as a variable name | repros | still-valid-keep-open | [link](https://godbolt.org/z/bsEPd3eaY) |
| [5681](https://github.com/microsoft/DirectXShaderCompiler/issues/5681) | InterlockedMax on templated Load<T>() result: ICE | does-not-repro | **close-fixed** | [link](https://godbolt.org/z/vfcsj3ThG) |
| [5682](https://github.com/microsoft/DirectXShaderCompiler/issues/5682) | Plain `install` target tries to install unbuilt llvm-as | not-compiler-verifiable | still-valid-keep-open | skipped |
| [5686](https://github.com/microsoft/DirectXShaderCompiler/issues/5686) | Amplification payload-size check wrong after -link | repros | still-valid-keep-open | skipped |
| [5703](https://github.com/microsoft/DirectXShaderCompiler/issues/5703) | RDAT missing after linking to a concrete profile (by design) | repros | enhancement-not-bug | skipped |
| [5704](https://github.com/microsoft/DirectXShaderCompiler/issues/5704) | -Qstrip_reflect doesn't strip names across lib->link [stale] | changed-behavior | needs-human-judgement | skipped |
| [5721](https://github.com/microsoft/DirectXShaderCompiler/issues/5721) | Linker never sets DXC_OUT_PDB | repros | still-valid-keep-open | skipped |
| [5723](https://github.com/microsoft/DirectXShaderCompiler/issues/5723) | Revise DxilMetadataHelper error reporting | not-compiler-verifiable | needs-human-judgement | skipped |
| [5736](https://github.com/microsoft/DirectXShaderCompiler/issues/5736) | Linking a non-library input: null-deref crash | repros | still-valid-keep-open | skipped |
| [5737](https://github.com/microsoft/DirectXShaderCompiler/issues/5737) | -link -Qstrip_debug fails outright | repros | still-valid-keep-open | skipped |
| [5739](https://github.com/microsoft/DirectXShaderCompiler/issues/5739) | Linker's -Fd output isn't a real PDB | repros | still-valid-keep-open | skipped |
| [5744](https://github.com/microsoft/DirectXShaderCompiler/issues/5744) | ddx/ddy_fine sink into flow control | does-not-repro | **duplicate-of #8001** | [link](https://godbolt.org/z/vrMMYWr31) |
| [5748](https://github.com/microsoft/DirectXShaderCompiler/issues/5748) | Groupshared read allowed via patch-constant fn (hull lib) | does-not-repro | **close-fixed** | [link](https://godbolt.org/z/daqY8a3x8) |
| [5768](https://github.com/microsoft/DirectXShaderCompiler/issues/5768) | SV_VertexID as float: caught late (validator, not Sema) | repros | still-valid-keep-open | [link](https://godbolt.org/z/PWdbvjGP3) |
| [5790](https://github.com/microsoft/DirectXShaderCompiler/issues/5790) | Enable "require conversation resolution" repo setting? [stale] | not-compiler-verifiable | needs-human-judgement | skipped |
| [5801](https://github.com/microsoft/DirectXShaderCompiler/issues/5801) | SM6.7 texture-offset range check skipped | repros | still-valid-keep-open | [link](https://godbolt.org/z/WT19a1jbM) |
| [5804](https://github.com/microsoft/DirectXShaderCompiler/issues/5804) | UBSAN alignment checks disabled in CMake | repros | still-valid-keep-open | skipped |
| [5807](https://github.com/microsoft/DirectXShaderCompiler/issues/5807) | Enum-shift implicit conversion wrongly rejected | repros | still-valid-keep-open | [link](https://godbolt.org/z/dE4KrbPjY) |
| [5823](https://github.com/microsoft/DirectXShaderCompiler/issues/5823) | [SPIR-V] Partial-spec static member SIGSEGV [stale] | changed-behavior | still-valid-keep-open | [link](https://godbolt.org/z/dsK39nrKE) |
| [5824](https://github.com/microsoft/DirectXShaderCompiler/issues/5824) | Move two clang-diagnostic tests out of ValidationTest.cpp | not-compiler-verifiable | still-valid-keep-open | skipped |
| [5848](https://github.com/microsoft/DirectXShaderCompiler/issues/5848) | Possibly-spurious -Wpayload-access-trace warning | inconclusive | needs-repro-from-reporter | [link](https://godbolt.org/z/d1a7E9Mxj) |
| [5849](https://github.com/microsoft/DirectXShaderCompiler/issues/5849) | RDAT never records whether PAQ was used | repros | still-valid-keep-open | skipped |
| [5883](https://github.com/microsoft/DirectXShaderCompiler/issues/5883) | const struct init folds pre-mutation values | repros | still-valid-keep-open | [link](https://godbolt.org/z/s7WdTna8d) |
| [5924](https://github.com/microsoft/DirectXShaderCompiler/issues/5924) | Swizzle on dependent-typed scalar rejected | repros | still-valid-keep-open | [link](https://godbolt.org/z/h5q7acrv9) |
| [5961](https://github.com/microsoft/DirectXShaderCompiler/issues/5961) | float-to-int literal-conversion warning names wrong value | repros | still-valid-keep-open | [link](https://godbolt.org/z/95MndY74x) |
| [5971](https://github.com/microsoft/DirectXShaderCompiler/issues/5971) | ASAN alloc_dealloc_mismatch false positive (Ubuntu libc++) | not-compiler-verifiable | needs-human-judgement | skipped |
| [5985](https://github.com/microsoft/DirectXShaderCompiler/issues/5985) | DllMain LoadLibrary(dxil.dll) under the loader lock [stale] | does-not-repro | needs-human-judgement | skipped |
| [5987](https://github.com/microsoft/DirectXShaderCompiler/issues/5987) | Struct-in-struct assign into amp-shader payload: ICE | repros | still-valid-keep-open | [link](https://godbolt.org/z/YoavsEvns) |
| [5993](https://github.com/microsoft/DirectXShaderCompiler/issues/5993) | ClangTidy: uninitialised branch in libclang/CIndex.cpp | repros | still-valid-keep-open | skipped |
| [5999](https://github.com/microsoft/DirectXShaderCompiler/issues/5999) | globallycoherent lost only through a function template | repros | still-valid-keep-open | [link](https://godbolt.org/z/E16q13zKa) |
| [6001](https://github.com/microsoft/DirectXShaderCompiler/issues/6001) | Hull-shader control-point pass-through not optimized | repros | still-valid-keep-open | [link](https://godbolt.org/z/nM3en9K5b) |
| [6003](https://github.com/microsoft/DirectXShaderCompiler/issues/6003) | [Valgrind] uninitialised SourceLocation::ID branch | not-compiler-verifiable | needs-human-judgement | skipped |
| [6005](https://github.com/microsoft/DirectXShaderCompiler/issues/6005) | ODR-use assert on a template-name/vector-alias collision | repros | still-valid-keep-open | [link](https://godbolt.org/z/h7WEM3v8G) |
| [6016](https://github.com/microsoft/DirectXShaderCompiler/issues/6016) | Large HS/DS/VS IO: signature-packing failure is now a crash | repros | still-valid-keep-open | [link](https://godbolt.org/z/h7YxEKKT5) |
| [6073](https://github.com/microsoft/DirectXShaderCompiler/issues/6073) | Templated struct's non-const static member: Comdat crash | repros | still-valid-keep-open | [link](https://godbolt.org/z/17nh9j5fW) |
| [6082](https://github.com/microsoft/DirectXShaderCompiler/issues/6082) | Bool-matrix ray-payload field bitcasts to i32 | repros | needs-human-judgement | [link](https://godbolt.org/z/zxjbnx5dE) |
| [6084](https://github.com/microsoft/DirectXShaderCompiler/issues/6084) | Add clang-cl Windows build to normal CI pipeline | not-compiler-verifiable | still-valid-keep-open | skipped |

## Per-issue findings

### The 7 close-fixed issues

Two of the seven (`#4965`, `#5748`) were checked against the full stable catalog back to
v1.4.1907; the other five have a later bisection floor because the feature under test genuinely
postdates the older releases — `#5261`/`#5681` at v1.6.2104 (`cs_6_6`/
`ResourceDescriptorHeap`), `#5080`/`#5563`/`#5587` at v1.6.2112 (SPIR-V debug info / HLSL 2021,
respectively) — and every excluded older release is confirmed `invalid-probe`, not silently
scored clean. All seven have a `complete` repro reproduced against the reporter's own filed
source and a Compiler Explorer link corroborating both ends. None of the seven commit-level
attributions were confirmed by building the candidate — that would need a detached worktree,
its own build, and this batch's constraints (no rebuild/relink of any shared target) ruled it
out for a single-issue session — so every one is stated as "strong, not certain" and the
*release* boundary, not the commit, is the load-bearing claim.

- **[#4965](https://github.com/microsoft/DirectXShaderCompiler/issues/4965) — `int f(int)` as
  `/E` crashes with an access violation.** `-E f` on a function that is *also* called at global
  scope to initialize a static makes DXC's entry-point wrapper call `f` from inside `f`'s own
  wrapper — genuine self-recursion introduced by lowering, not by the source. Every release
  v1.4.1907–v1.8.2502 crashes on it (a silent AV, a printed AV, or `llvm::cast<X>()` E_FAIL
  depending on release/build); v1.8.2505 onward gives a clean `recursive functions are not
  allowed` diagnostic instead, because the front end's own recursion check now runs before the
  pass that used to crash. `internal_failure` covers all three historical shapes; `--repeat 10`
  confirms 0/10 hits on ground truth (deterministic, not a lucky clean run). 162-commit window,
  no candidate commit named.
- **[#5080](https://github.com/microsoft/DirectXShaderCompiler/issues/5080) — cbuffer assert
  with `-fspv-debug=vulkan-with-source`.** Fixed at v1.8.2405 (last bad: v1.8.2403.2). The
  automatic bisection needed one hand correction: v1.6.2112's capture read "clean" only because
  it also rejects the reporter's `-fspv-target-env=vulkan1.3` value outright (a second instance
  of the `-fspv-debug` option-value trap already known from batch-018/#7300 — see **Method
  lessons**); re-probed with `vulkan1.0` it crashes like every other pre-fix release, pushing
  the true floor back to v1.6.2112, the oldest release able to parse the mode at all. Candidate
  fix: `1e59ce9185` (#6531), which removes the exact assert quoted in the issue and matches the
  in-thread `-fvk-use-dx-layout` diagnosis; a build-verification attempt was made and abandoned
  when the parent commit's toolchain (CMake 4.3.1, MSVC 14.51) rejected both a removed
  `cmake_policy` and a now-forbidden `/WX` warning — a genuine toolchain-drift dead end, not a
  shortcut taken.
- **[#5261](https://github.com/microsoft/DirectXShaderCompiler/issues/5261) — deadlock loading
  `RayDesc` from `ByteAddressBuffer`.** Regressed-then-fixed, not a standing bug: clean
  v1.6.2104–v1.7.2207, hangs v1.7.2212–v1.8.2502 (`any_of(timeout, internal_failure)`, since
  Release archives hang where a Debug build the maintainer ran in 2023 asserted — every `repro`
  in the regressed range is a measured `TIMEOUT`, confirming both predicate arms are load-bearing,
  not decorative), clean again from v1.8.2505. The filed repro never reads the loaded `RayDesc`,
  so a clean compile alone would under-test the claim; a control that consumes every field
  confirms the SROA pass now genuinely flattens the load (four `rawBufferLoad.f32` calls at the
  right byte offsets) rather than merely not crashing on dead code. Candidate fix `053e7ac65`
  (PR #7440) is the only commit in the window touching the relevant file, but its own tracked
  issue (#7434) is a *different* RayDesc pattern — see **Cross-issue analysis** for why this
  same commit is also #5681's leading candidate.
- **[#5563](https://github.com/microsoft/DirectXShaderCompiler/issues/5563) — "found
  unregistered decl" on a partial template specialization (SPIR-V).** Fixed at v1.9.2602 (last
  bad: v1.8.2505.1). The filed shader's unused local is dead-code-eliminated by default, so a
  clean run alone would be weak evidence; an `-Od` control shows the static member genuinely
  resolves (`OpConstantTrue`, a real `OpStore`) rather than the code path merely being skipped.
  Two candidate commits in the 229-commit window touch the exact mechanism
  (`1e3da156b`/#7673, "Handle partial template class specialization", and `b9af1ec44`/#7786,
  generalising constant-variable folding to explicit `bool` decls); which one is load-bearing
  for *this* repro was not determined. `text_stale`: the title reads as present-tense on an
  issue that is still open.
- **[#5587](https://github.com/microsoft/DirectXShaderCompiler/issues/5587) — bitfield
  initialization order-dependence.** Fixed at v1.8.2505 (last bad: v1.8.2502); the bisection
  floor is v1.6.2112 (HLSL 2021's own floor), not v1.4.1907, since bitfields postdate every
  older release. The emitted DXIL was read, not just the exit code: ground truth's
  `rawBufferStore` writes a concrete `0` into the correct 32-bit lane, matching the reordered
  control that the reporter already said worked — so this is a real fix, not a compile that
  merely stopped erroring while emitting something else. No candidate commit found in the
  162-commit window despite a targeted search of the flattening-relevant files; stated as
  release-level only, deliberately.
- **[#5681](https://github.com/microsoft/DirectXShaderCompiler/issues/5681) —
  `InterlockedMax` on a templated `Load<T>()` field: ICE.** Fixed at v1.8.2505 (last bad:
  v1.8.2502); floor is v1.6.2104 (`cs_6_6`/`ResourceDescriptorHeap`). Same candidate commit as
  #5261 (`053e7ac65`), independently re-derived from a fresh grep of the same window — see
  **Cross-issue analysis**.
- **[#5748](https://github.com/microsoft/DirectXShaderCompiler/issues/5748) — groupshared
  read allowed through a hull shader's patch-constant function in a library target.** Fixed at
  v1.9.2607 (last bad: v1.9.2602.24, built 2026-05-27) — the tightest boundary of the seven,
  and the only one where GitHub's own blame API pinned the responsible lines to a specific PR
  (#8140, `c44a383b4`, "Add GroupSharedLimit attribute support for Mesh, Amp and Node shaders")
  whose diff visibly adds the missing `M.IsPatchConstantShader(&F)` disjunct. Flagged
  explicitly: that PR *merged* 2026-02-13, five months before the release that first shows the
  fix — consistent with a release-train branch point that predates the merge, not a
  contradiction of the direct behavioural measurement, but worth stating plainly rather than
  papering over the gap.

### A close-but-not-quite: `does-not-repro` without `close-fixed`

**[#5985](https://github.com/microsoft/DirectXShaderCompiler/issues/5985) — `DllMain` calls
`LoadLibrary` for `dxil.dll` under the loader lock.** The *specific* hazard is fixed: PR #7451
(`77b2ff676`, merged 2025-06-05, 479 commits behind ground truth) removed
`dxcompiler.dll`'s own `DxilLibInitialize()`/`LoadLibrary` call entirely, in favour of a
statically-linked validator. But the identical pattern is still live, unfixed, and un-named by
the issue, in the sibling `tools/clang/tools/dxrfallbackcompiler/DXCompiler.cpp`. `does-not-repro`
for the literal report, `needs-human-judgement` rather than `close-fixed` for the recommended
action, since closing it would also close the door on the still-open sibling defect the issue
never mentions. `text_stale`: see below.

### Changed-behavior (4)

- **[#4805](https://github.com/microsoft/DirectXShaderCompiler/issues/4805) — custom
  `IDxcIncludeHandler` ignored for `-Zi` debug source.** The *reported* 2022 crash is gone (the
  disk-read fallback has been wrapped in `catch(...)` since 2020), but the underlying defect —
  `EmitVisitor.cpp`'s `ReadSourceCode` never consults the caller's include buffer, only its own
  raw disk re-read — is fully present and, since PR #7662 narrowed a silent wrong-content
  fallback in 2025, now a **harder** failure (`fatal error: generated SPIR-V is invalid`) than
  originally reported, not a softer one.
- **[#5059](https://github.com/microsoft/DirectXShaderCompiler/issues/5059) — SCEV widens a
  guarded loop multiply to an illegal `i33`.** Two predicates bisected separately rather than
  combined, deliberately: the *reported* silent shape (`i33` reaching disassembly) reproduced
  through v1.9.2602.24 and stopped at v1.9.2607; the *validator-caught* shape is the exact
  mirror image. Combining them with `any_of` would have hidden the one fact worth reporting —
  confirmed with `-Vd` that ground truth still internally builds the identical illegal
  sequence, so the defect never left, only the DXIL validator's own width check (plausibly
  PR #8207, not confirmed) started catching it.
- **[#5704](https://github.com/microsoft/DirectXShaderCompiler/issues/5704) —
  `-Qstrip_reflect` doesn't strip names across a `lib_6_3`→linked `cs_6_3` boundary.** Two
  separate findings, not one: the reported stripping defect reproduced exactly as filed against
  v1.7.2308 and is independently confirmed fixed from v1.8.2403 (tested via an adapted repro
  carrying the `[shader("compute")]` attribute the current front end now requires); separately,
  and in the same window, the *literal* unattributed repro stopped being linkable at all for an
  unrelated reason. This issue is also where the batch's stale-output-file hazard was found —
  see its own section below.
- **[#5823](https://github.com/microsoft/DirectXShaderCompiler/issues/5823) — SIGSEGV on an
  out-of-line partial-specialization static member (SPIR-V).** The crash is fixed since
  v1.7.2308 (PR #8079, confirmed by reproducing that PR's own regression test), but the fix's
  guard (`getDescribedClassTemplate()`) only matches a *primary* template's pattern, not a
  `ClassTemplatePartialSpecializationDecl` — so the original repro still fails to compile today,
  just with a diagnosed `casting to type 'void' unimplemented` instead of a crash. A fuller
  matrix across template-kind × out-of-line spelling separates this from the later, related
  `'const' is not a valid modifier` reports (#6677, correctly closed not-planned for a different
  reason) and the still-silent illegal-`static`-duplication acceptance.

### Enhancement / not a bug (6)

`5172`, `5173`, `5175` (`IDxcIndex`/`IDxcCursor` COM-API surface gaps — genuine, but a missing
parameter/accessor rather than a defect); `5395` (no shadow warning for an HV2021-scoped loop
variable — DXC has no general shadow diagnostic in any language mode, so nothing "regressed");
`5448` (a validator code-organization request, confirmed unimplemented by source and by
`git log --all --grep`, with its one externally-observable consequence unreachable from
ordinary HLSL); `5703` (RDAT is by-design library-only — a finalized/linked container never
carries it, in any release, confirmed against a direct compile to the same profile).

### Duplicate

[**#5744**](https://github.com/microsoft/DirectXShaderCompiler/issues/5744) (`ddx_fine`/`ddy_fine`
sinking into flow control) is fixed on `main` (`28d9915fa0`, PR #8707, merged 2026-07-31, two
days after the newest catalogued release) — but the fix landed against **#8001**, a later-filed
report of the identical defect, so #5744 itself was never closed. Found only by reading #5744's
own cross-reference timeline in step 1 and recognising #8001's description as the same defect,
per the standing "read the timeline before touching the compiler" lesson.

### `not-compiler-verifiable` and `inconclusive` (18)

Seventeen genuine non-compiler questions (COM/API surface, CI/build configuration, docs,
platform sanitizer findings, a GitHub repo-settings toggle) and one `inconclusive`
(**#5848**, a reconstructed repro that could not reproduce the reported warning on either
`main` or the exact named release — source reading shows the checked code path is gated on a
non-null payload, which raygeneration's own snippet never has, so the reconstruction may simply
differ from the reporter's real project code; `needs-repro-from-reporter` rather than a forced
verdict). Every one of the 17 states explicitly *why* no `cmd.txt`/Compiler Explorer link
exists rather than leaving the absence implicit — several (`5064`, `5169`, `5546`, `5824`, `5971`)
still measured their underlying **technical premise** against source or a live external
resource even though the *deliverable* (a CI job, a docs page, someone else's repo) is outside
this repository. The remaining twelve: **`4766`** (a CMake `SHARED`-vs-`STATIC` library-target
ask, unaddressed since the tool's first commit, with a related open issue — #5985 below —
raising the same question independently); **`5309`** (a bare `0x8007007E` decoded to
`HRESULT_FROM_WIN32(ERROR_MOD_NOT_FOUND)` and traced to a single `LoadLibraryExW` call site in
`dxbc2dxil.cpp`, without being able to run the actual converter in this environment);
**`5350`** (SM6.8 Work Graph reflection — two concrete API gaps confirmed absent from the
current interfaces, one with an open, unreviewed PR); **`5436`** (a requested defensive assert
for the validator's opcode switches, confirmed still absent by source and by
`git log --all --grep`); **`5476`** (a macOS-only Unicode-conversion bug that no compiler in
this toolkit — Windows `main-debug` or CE's Linux panes — can trigger, since none reproduces
the failing locale state; a plausible fix, `9bcce409b`, has landed since the last "still
repros" comment but was not independently confirmed); **`5481`** (a Windows/CI code-coverage
gap, with an earlier attempted fix, #5510, closed unmerged); **`5595`** (a `lit`
hash-stability test-format request); **`5682`** (the plain `install` CMake target tries to
install an `llvm-as` that `EXCLUDE_FROM_ALL` never built — confirmed by reading the CMake rule
graph, not by running an install); **`5723`** (a metadata-error-reporting redesign whose
reference implementation branch has sat unmerged since the day the issue was filed); **`5790`**
(a GitHub branch-protection/ruleset setting, checked live against the API rather than the 2023
text — see `text_stale`); **`6003`** (a Valgrind finding on `TypeLoc::getBeginLoc()`
that this Windows environment cannot re-run; a *second*, related Valgrind finding in the same
issue is independently confirmed already fixed, by source, since before filing); **`6084`** (no
`clang-cl` Windows CI job exists at all, not even the release-only one described, and the PR
that would have added it lapsed unmerged for inactivity).

### Everything else — `repros`, `still-valid-keep-open` (grouped by theme)

- **Rewriter (`dxr.exe`/`IDxcRewriter2`) reachability bugs, five issues, one shared root
  cause:** `5255`, `5268`, `5290`, `5292` all trace to the same gap in
  `VarReferenceVisitor`/`CollectRewriteHelper` (`tools/clang/tools/libclang/dxcrewriteunused.cpp`):
  declaring or casting to a type is never itself "using" it, and a `TypedefDecl` is never added
  to any removal-candidate set at all. `5423` is a different rewriter defect (dxr.exe's
  `RewriteWithOptions` call site never forwards parsed `-D` values to the rewrite functions,
  despite the unmerged fix in #5424 existing since 2023).
- **Linker (`dxc -link`/`IDxcLinker`), seven issues:** `5686` (amplification payload-size check
  wrong after linking — two compounding bugs, one shared with `5269`/`5668` below, one in the
  linker's own missing `setDataLayout`), `5721` (`DXC_OUT_PDB` never wired into the linker's
  output set — PR #6834 open, unmerged), `5736` (null-deref linking a non-library container),
  `5737`/`5739` (`-Qstrip_debug`/`-Fd` interactions produce a broken or unreadable PDB — PRs
  #6833/#6834 both open, unmerged).
- **Amplification-shader empty/small payload validation, three issues, one line of code:**
  `5269` and `5668` (filed three months apart, independently reaching the identical
  `ValidateAsIntrinsics` finding) and `5686` (the same check, wrong for a second, linker-specific
  reason). See **Cross-issue analysis**.
- **Front-end diagnostics and type system:** `5115` (integer-literal overload ranking), `5338`
  (array-cast crash that FXC instead constant-folds), `5389` (bare-literal swizzle typing,
  shares a root cause with the already-closed #5082), `5554` (C++11 enum-as-constant), `5674`
  (`matrix` shadowable as a variable name, regressed by the 2022 name-lookup rework), `5807`
  (enum/shift conversion), `5924` (swizzle on a dependent scalar type), `5999`
  (`globallycoherent` lost only through a function template), `6073` (templated static-member
  Comdat crash).
- **Missing/wrong diagnostics on otherwise-silent codegen:** `4871` (`inout` pre-decrement
  silently subtracts 2, not 1 — a genuine miscompile, not a crash; regressed at v1.5.2010),
  `4888` (an unsupported `ResourceDescriptorHeap` array pattern surfaces the validator's generic
  "All metadata must be used" instead of a real diagnostic; a related SPIR-V assert on the same
  issue is separately confirmed fixed since v1.8.2405), `5039`/`5040` (uninitialized
  buffer-load index), `5165` (switch lookup-table `i8` truncation), `5417` (signature "Used"
  mask misses `GetAttributeAtVertex`), `5573` (spurious "unused" after resource assignment),
  `5633` (no static out-of-bounds warning), `5768` (SV_VertexID type error caught only at
  validation), `5801` (SM6.7 offset range check skipped), `5883` (const-qualified struct init
  folds pre-mutation values), `5961` (a `-Wliteral-conversion` warning names the wrong resulting
  value — right magnitude, wrong sign, for every negated-literal case), `5987` (struct-in-struct
  assign into an amplification payload).
- **Command-line/driver plumbing:** `5072` (`-Fh` sentinel identifier), `5116` (cs_6_6 accepts
  what cs_6_5 correctly rejects), `5117`/`5416` (`-M`/`-MD`/`-MF` swallow diagnostics or skip
  `-Fo` entirely), `5302` (`dx.break` guard missing outside PS/CS/Lib stages), `5328` (dead but
  reachable-in-principle null-`IRBuilder` risk in the linker-only matrix-bitcast pass), `5491`
  (wave intrinsics never marked side-effect-free, so DCE can't remove an unused call), `5567`
  (comma-in-init warning scope), `5632` (construct-cast crash plus a related missing
  diagnostic), `6001` (hull control-point pass-through never optimized), `6005` (ODR-use assert
  from a template/vector-alias name collision), `6016` (a signature-packing diagnostic became
  an `llvm_unreachable`, so a legitimate limit now crashes instead of erroring), `6082` (bool
  matrices in ray payloads still bitcast through `i32`, a design question more than a bug).
- **Build, platform and header conflicts:** `4786` (x86-only ABI corruption in the legacy DXBC
  converter, fixed once, reverted for AMD driver compatibility, still broken), `4792` (a
  documented, still-open concurrency race in pass registration; this session's own bounded
  multithreaded probe could not trigger the platform-specific Linux/glibc manifestation, and
  says so rather than claiming a negative), `5079` (DXC's own non-Windows `WinAdapter.h` shim
  conflicts with DirectX-Headers' equivalent shim; a fix exists, PR #8431, stalled on two
  unresolved ABI-visibility design questions its own author raised), `5804` (UBSAN's alignment
  check is deliberately excluded from both sanitizer CMake configurations), `5993` (a ClangTidy
  uninitialized-branch finding in `libclang/CIndex.cpp`, with an approved-but-never-merged fix,
  PR #6002, closed unmerged by the same two-year inactivity sweep pattern documented for #2427
  and #6084).
- **Extended reflection/PIX-style gaps:** `4858` (illegal code motion sinks
  `CalculateLevelOfDetail` into a branch), `4914` (aggregate `this` has no CodeGen visitor),
  `4958` (SROA crash on unused hull-shader globals), `5105` (no reflection entry for unused
  resources — two open PRs already track it), `5184` (`WaveMatch` with a vector argument),
  `5194` (can't template an `operator()` overload), `5244` (SPIR-V `RWTexture2DMS` gap), `5258`
  (bit-field `FlattenedTypeIterator`, three sub-claims scored separately), `5357` (missing type
  annotation on a chained node-record intrinsic call), `5434` (no validation for
  `Annotate*Handle` intrinsics reached only via hand-authored DXIL), `5849` (RDAT never records
  whether PAQ was used).

## Cross-issue analysis

Collation is where a shared root cause across independently-triaged issues can actually be
checked, per `SKILL.md`'s own rule that a per-issue worker records a "this looks like #NNNN"
suspicion in `method-notes.md` and leaves the draft silent. Three genuine clusters this batch:

**#5269, #5668 and #5686 are one validator defect, wearing three faces.** All three were
triaged independently (filed three months apart in two cases) and each landed on the same
line: `ValidateAsIntrinsics` (`lib/DxilValidation/DxilValidation.cpp`) measures an
amplification-shader payload's *pointer* type (`OperandVal->getType()`), not its dereferenced
struct, so the "declared vs. actual size" check is really "declared vs. pointer size" — a
constant 4 bytes on DXIL's own data layout. #5269 and #5668 hit this because an **empty**
struct's real size (0) is the one case smaller than that constant; #5686 hits a *second*,
compounding bug on top of it — `DxilLinkJob::Link` never calls `setDataLayout`, so a linked
module silently inherits LLVM's default 8-byte pointer size, and the same vacuous check now
fires on any payload **under 8 bytes**, empty or not. A fix to the validator's own type
dereference would resolve #5269/#5668; #5686 additionally needs the linker's missing
`setDataLayout`, or either half alone still misfires for it. None of the three drafts assert
this cross-linkage — it is recorded here, per the per-issue brief's own instruction, as
collation's judgement to make.

**#5261 and #5681 independently name the same fixing commit.** Both are `close-fixed`
verdicts in the same v1.8.2502→v1.8.2505 window; both, working from completely different
repros (a `RayDesc` load hang/assert vs. an `InterlockedMax` ICE on a templated `Load<T>()`
result) and different call sites, converged on `053e7ac65` (PR #7440, "Refactor udt intrinsic
arg copy to before SROA, flatten RayDesc") as the leading candidate — the only commit in each
issue's own narrowed window touching the relevant file. Neither issue's own tracked bug
(#7434, a `HitObject`/`TraceRay` pattern) is either of these two, so the commit's *systemic*
change (moving UDT-typed intrinsic-argument copy-in/copy-out generation to run before SROA,
rather than its named special-cased intrinsics) is doing the work for both. This is
independent corroboration, not proof: two different symptoms both plausibly explained by one
systemic mechanism change is stronger evidence than either attribution alone, but the exact
mechanism was not built and tested in isolation for either issue, and both drafts already say
so. Recorded here rather than in either `comment.md`.

**Five `dxr.exe`/`IDxcRewriter2` issues share one root gap, and #5290's own notes predicted
#5255 belongs to a different one.** `5255`, `5268`, `5290` and `5292` all trace to
`VarReferenceVisitor`/`CollectRewriteHelper` (`dxcrewriteunused.cpp`) never treating a
declaration or a cast as a "use" of a type, and never adding a `TypedefDecl` to any
removal-candidate set — one code change plausibly fixes all four. #5255's own `notes.md`
(triaged earlier in the same worker's session, before #5290) independently found and named
exactly #5290's headline defect ("the entry function's own parameters are never marked as used
types") as a side observation, word for word — a striking, easily-missed near-duplication that
a worker restricted to its own issue correctly declined to assert as a formal `duplicate-of`,
since #5255's *own* headline defect (a cbuffer-referenced struct) is unrelated. `5423` is a
different rewriter defect (a dropped `-D` value, not a reachability gap) and is not part of
this cluster.

Two workers independently discovering the same tooling trap and two independently discovering
the same shared root cause are both treated with the same weight `SKILL.md` gives them:
stronger evidence than either alone, and — for the traps — justification for a tool change
rather than only a documentation note. See **Method lessons**.

## The #5704 stale-output-file cross-release contamination hazard

This is the most consequential finding of the batch, both for what it could have done to
**this** issue's verdict and for what it says about every other multi-line `cmd.txt` in the
207-issue tree.

**The mechanism.** #5704's repro is a 3-line pipeline: compile a library, `-link` it to a
concrete profile, `-dumpbin` the linked container. `run`/`bisect`'s ordinary probe path
(`_run_probe_command_list`) copies the issue directory into an isolated scratch copy before
each release probe — but only to protect **declared inputs** from mutation; it does not clear a
**declared output** first. dxc only rewrites a `-Fo`-style target on success, and every release
probed in one sweep shares the same issue directory as its scratch seed. So a release whose own
`-link` step fails (as genuinely happens here from v1.8.2403 onward, for an unrelated reason —
see #5704's own findings above) leaves *nothing* to overwrite the previous release's
`linked.bc` — and the pipeline's third line still runs, `-dumpbin`-ing whichever release's
container happens to be sitting there.

**The proof, not an inference.** `out-v1.6.2106.txt` (link exit 0) and `out-v1.9.2607.txt`
(link exit 1, `Cannot find definition of function main`) were captured in the *same* sweep at
the identical timestamp. Both `-dumpbin` sections are **byte-identical**: the same embedded
shader hash (`7023918e6966b36ebde405470921951d`), the same `"clang version 3.7
(tags/RELEASE_370/final)"` identifier, and — the detail that puts this beyond doubt — the same
`!dx.valver = !{!2}` / `!2 = !{i32 1, i32 6}` (validator version 1.6) in *both* captures, even
though v1.9.2607's own `-dumpbin` reader is visibly newer (its output additionally prints a
`PSVRuntimeInfo:` block that v1.6.2106's reader does not emit at all). v1.9.2607 disassembled
v1.6.2106's leftover file with its own, newer reader — not its own (never-produced) output.

**What this could have done, undetected.** Had the worker not caught this, the automatic sweep
would have scored every release from v1.8.2403 onward as `repro` (since the stale disassembly
still matches `\btexResource\b|\brwTexResource\b`), reporting "always reproduces, still open" —
completely erasing the fact that the reported defect, tested with a currently-valid equivalent
repro, is fixed at v1.8.2403. That is the *more dangerous* direction of error `SKILL.md`
already names for a crashed probe: a real fix silently reported as "never happened."

**Disposition — both captures kept, not fixed by hand.** `out-v1.6.2106.txt` and
`out-v1.9.2607.txt` are left exactly as produced; hand-editing a capture is the falsification
this whole workflow exists to prevent, and they are the *proof* the hazard exists. The
corrected release history came from an issue-local matrix (`measure.py`/`measure-variant.py`)
that gives every release its own freshly created and freshly deleted scratch directory and
scores a release `invalid-probe` whenever its own `-link` step fails to produce the file the
next line needs.

**Promoted, this session.** `_run_probe_command_list` now computes, for every probe, which
files this command list both writes (via an `OUTPUT_VALUE_FLAGS` option such as `-Fo`/`-Fd`)
*and* separately reads elsewhere in the same `cmd.txt` (a later line's positional argument or a
non-output flag's value) — `declared_output_tokens()` — and deletes those specific files from
the scratch copy before running. A release whose own earlier line fails to regenerate one then
meets a genuine absence (an ordinary "file not found") instead of a stranger's leftover.
Deliberately narrower than "clear every declared output": a file named only once, purely as a
single line's own output, is untouched — that shape is exactly what the pre-existing `-P`/`-Fi`
spelling-retry regression test (#3044) pre-arms to test a different hazard (an old release's
parser treating the mere *presence* of a value-flag target differently), and clearing it
unconditionally would have silently defeated that test's premise. Verified in both directions:
a new regression test in `test_predicates.py` fails without the fix (reproducing exactly
#5704's byte-identical-stale-read signature against a fake two-release sweep) and passes with
it; the existing `-P`/`-Fi` test continues to pass unchanged. Documented in `SKILL.md` next to
the closely related, already-documented "never point a release-sweep *script* at the same
output filenames as ground truth" hazard — this is the same failure shape occurring inside the
tool's own native runner, for any current or future multi-line pipeline, not only a
hand-written sweep script.

**Blast radius checked, not merely fixed going forward.** Before deciding this was worth a code
change, the corpus was searched for every issue whose `cmd.txt` has more than one line
(19 issues across the full 207-issue tree, both `batch-019` and earlier batches). Of those,
`#3005`, `#4168`, `#5040` and `#5739` share #5704's exact structural shape (an earlier line
writes a file, a later line reads it back); their captures were checked for the same
tell — byte-identical content across releases whose earlier-line exit codes differ — and none
showed it: every capture's content hash is distinct, consistent with each release genuinely
producing its own fresh output rather than reading a predecessor's. `#5736`/`#5737`/`#5686` are
two-line pipelines whose reported symptom is the *linking* line's own direct output, with no
third line reading a possibly-stale artifact, so they were never exposed to this specific
shape. **#5704 is the confirmed, sole instance of this hazard actually manifesting in the
corpus today** — the fix protects every future multi-line issue, and this batch's report is
the place that says so rather than leaving readers to assume the worst about every other
release-history table in the tree.

## Method lessons

54 of the 100 issues carry a `method-notes.md`; every one was read in full. What follows is the
disposition of every candidate lesson found there, not just the ones that changed something —
per `SKILL.md`'s instruction to record what was rejected, superseded or left open as
explicitly as what was promoted.

### Promoted this session (`SKILL.md` and/or `triage.py` changed, tests added)

1. **The #5704 stale-output-file hazard** (above). `_run_probe_command_list` now clears a
   probe's own scratch copy of any file it both writes and separately reads elsewhere in the
   same `cmd.txt`, before running. New test in `test_predicates.py`; confirmed to fail without
   the fix and pass with it.
2. **`git log --all -S`/`--is-ancestor` can be fooled by this checkout's shallow-fetch/
   multi-remote history, not only by history rewrites.** Independently hit twice: `#5172` and
   `#5436` each dated a *different* symbol's introduction to the same commit, `8a8b29f96`
   ("[spirv] AMD work graphs extension"), which `git show --stat` shows adding the entire
   containing file as new — the signature of a graft or foreign-branch boundary, not a real
   edit — and which fails `merge-base --is-ancestor` against ground truth for both. `#5993`
   independently hit the same root constraint from a different angle (a bare `git rev-list
   --count` from ground truth shows only ~200 reachable commits, so "no commits touch this
   file" from local `git log` can be a shallow-clone artifact). `SKILL.md` now requires
   `merge-base --is-ancestor <found-sha> <ground-truth-sha>` before citing any `--all`-found
   commit as an origin, and recommends `git rev-parse --is-shallow-repository` as a pre-flight
   check before trusting local history for dating or a "nothing changed" claim. Two independent
   sightings of the identical false positive is exactly the repeated-trap signal `SKILL.md`
   already treats as justifying a rule rather than a one-off reminder.
3. **An unbounded "X appears after Y" regex over full DXIL disassembly matches the trailing
   `declare` line for every intrinsic the module calls, regardless of where the real call
   sites are.** Measured on `#4858`: a first-draft predicate for "the call was sunk into the
   branch's successor block" matched even the `-Od` control, which does not sink the call at
   all, because the non-greedy scan simply kept going until it hit the trailing `declare
   float @dx.op.calculateLOD.f32(...)` line every capture has. Documented in step 4's
   IR-portability guidance: bound the scan with a negative lookahead excluding the next label
   and the function's closing brace, and require `call` immediately before the opcode name.
4. **An FXC Compiler Explorer pane needs an FXC-supported profile, not the repro's own `-T`.**
   Measured on `#5338`: reusing the repro's `vs_6_0` made the pane fail with `Unsupported
   shader model specified`, a fact about FXC having no SM6 family at all, not about the
   construct under test. Documented next to the existing "FXC panes need controls too"
   guidance in step 7.
5. **`bisect --linear`'s "non-monotonic history" label conflated a single clean transition with
   genuine oscillation**, because both produce `len(runs) != 1`. Measured on `#4871`: one clean
   regression at v1.5.2010, no reversion through v1.9.2607, printed as "non-monotonic history
   … transitions at v1.5.2010 -> repro" — technically accurate about the run count, misleading
   about the shape, and exactly the kind of description a reader could mistake for a
   fix-then-revert that never happened. `triage.py` now names a run of length 2 the same way
   binary search does (`regressed-in <tag> (last good: <tag>)` / `fixed-in <tag> (last repro:
   <tag>)`), reserving "non-monotonic" for a run of 3 or more. Refactored into a small, pure
   `describe_linear_result()` so it is testable without a compiler or a release catalog; six
   new unit tests cover the single-transition, no-transition and genuinely-oscillating shapes.
6. **A release can reject an unrecognised *value* of `-fspv-target-env`, not only of
   `-fspv-debug`** — the same trap class batch-018 partially fixed after `#7300`, recurring on
   a different flag. Measured on `#5080`: v1.6.2112's automatic capture read "clean" only
   because it also rejects the reporter's `-fspv-target-env=vulkan1.3`; re-probed with a value
   it accepts, it crashes like every later pre-fix release. `UNSUPPORTED_MARKER_RE` now
   recognises `unknown SPIR-V target environment`, anchored the same way as the existing
   `-fspv-debug` marker; a negative control confirms an ordinary mention of a valid target
   environment is not demoted. `reindex` found exactly the one expected disagreement
   (`#5080` v1.6.2112: `no-repro` -> `invalid-probe`) and no others; accepted and explained
   above and in **Evidence verification**.
7. **When the affected component is not built in this environment at all, a narrow externally
   checkable claim can be isolated into a standalone compile outside the CMake tree**, which is
   strictly stronger evidence than source reading and touches no shared build target.
   Independently used, in this batch, for two unrelated questions: `#4786` confirmed an
   x86-vs-x64 ABI claim (a `float` return silently quiets a signalling NaN on x86 cdecl) with a
   few-line `.cpp` compiled directly via `cl.exe`/`vcvarsall.bat`; `#5309` confirmed a specific
   Win32 error code (`HRESULT_FROM_WIN32(ERROR_MOD_NOT_FOUND)` from a guaranteed-missing
   `LoadLibraryExW` target) the same way. Documented next to the existing CMake-tree-parsing
   example (`#3276`) in the `not-compiler-verifiable` guidance.

### Documented as a named trap, not promoted to a classifier change (single sighting)

- **A newly-shipped, unrelated builtin can collide with a repro's own top-level identifier and
  manufacture a fake mid-bisect "fix".** Measured on `#5554`: v1.8.2405 briefly registered a
  builtin `integral_constant` in the global namespace (for `vk::SpirvType` support), so a repro
  that happens to declare its own `integral_constant` collides and gets an unrelated
  "redeclaration" diagnostic instead of the repro's real error — scoring that one release
  clean, sandwiched between reproducing releases on both sides. This is not a missing-*feature*
  marker (the release supports everything the repro needs) and is too narrow, on one sighting,
  to write a safe general classifier rule without risking a false demotion elsewhere. Recorded
  in `SKILL.md`'s prose as a distinct trap shape; the concrete generalisable check its own
  method-notes propose — reading a non-monotonic bisect's isolated "clean" release's raw
  capture before accepting it, which this issue's own worker did — is already covered by
  existing guidance, so nothing else needed changing this time.

### Reinforcements of already-documented lessons (confirmed working as designed; no new text)

Cited here only because `SKILL.md` asks collation to note how often a documented trap still
bites, without restating guidance that already covers it: `#5165` (oldest release's diagnostic
wording drifted — "message text is not portable, especially at the oldest release" caught it
on the first bisection pass, corrected by widening the regex); `#5744`/`#5768`/`#4766`/`#5105`
(the cross-reference timeline read in step 1 found the actual fix, a related PR, or a
maintainer's live position — the standing #6727 lesson); `#4914` (a `godbolt --compilers
"id:<args>"` override repeating the source filename produced a harness artifact, not a finding
— the same filename-repetition shape already documented for `-P`/`-Fi`, now confirmed for an
FXC-pane override too); `#5883` (a literal `%1` register anchor false-negatived on the one
release with named SSA values — the standing #3414 lesson); `#5290` (a repository-wide, not
path-scoped, `git log --all -S` check as a cheap "was this ever handled" probe — the standing
#2952 lesson); `#4805`/`#4888`/`#5261`/`#5389` (predicate compositions and per-format
instrument controls that are worked examples of, not exceptions to, the existing "one defect
two signatures" and "a control validates the instrument for the specific format under test"
guidance).

### Rejected as too narrow to promote (issue-specific, recorded and left in that issue's notes)

`#5292`'s finding that `dxr.cpp` passes `RewriteWithOptions` a `skipArgCount=0` argv (unlike
the `skipArgCount=1` convention used elsewhere) only matters to a worker driving that exact COM
entry point directly, which is rare enough that a `SKILL.md` line would mostly be noise; it
stays as a concrete, reusable data point in `#5292/method-notes.md` for whichever future issue
needs it. `#4792`'s specific `WaitForMultipleObjects` 64-handle ceiling is a real, useful fact
about *that* harness, not a general triage-method lesson. Both are exactly the shape `SKILL.md`
asks to leave local rather than force into shared guidance.

## Independent review (step 10)

Every draft's `verdict.json` records `reviewed_by: "gpt-5.3-codex (independent batch-019
step-10 review; applied selectively at collation)"` — confirmed present on all 100 issues, not
assumed. The review itself ran as four passes over disjoint slices of the batch (its own logs,
outside this repository, are the primary record; what follows is this session's read of them,
cross-checked against the actual `comment.md` files rather than trusted at face value).

- **Pass 1** (`4958`, `5039`, `5059`): tightened a release-history wording table to match the
  actual captures (splitting a claimed uniform range into the two sub-ranges the evidence
  supports), replaced a fork-local commit reference with the public ground-truth commit, and
  cut speculative fix-tractability language.
- **Pass 2** (`5261`, `5292`, `5309`, `5338`, `5434`, `5448`): reduced overstated certainty on
  the `#5261`/PR #7440 attribution to "a documented lead," trimmed a repeated ancillary
  observation, cut a speculative deployment narrative in `#5309` down to source-backed evidence
  plus an explicit missing-confirmation ask, and replaced deterministic wording ("gets emitted
  twice") with source-backed wording ("can still emit twice") in `#5448`.
- **Pass 3** (25 issues, `5476`–`5744`): softened `5476`'s "likely fix" to "plausible fix
  candidate" to match its own medium-confidence attribution, fixed a genuine profile/repro
  contradiction in `5632`'s Compiler Explorer parenthetical, and corrected a chronology typo in
  `5686`. Every other draft in this slice was read and kept as-is at high confidence.
- **Pass 4** (25 issues, `5748`–`6084`): nine concision/speculation edits — replacing
  speculative phrasing with measured-release phrasing (`5748`), tightening label-suggestion and
  action-recommendation wording (`5768`, `5993`, `6082`), removing forward-looking speculation
  while keeping the measured Clang-front-end result (`5807`), removing a speculative
  priority/probabilistic inference while keeping the factual milestone/PR status (`5824`,
  `6003`), and tightening unresolved-status wording without dropping the underlying caveat
  (`5849`). No numerals, version ranges or symbol names were altered in this pass beyond
  wording.

**No factual, numeral or quantifier error was reported across any of the four passes** — a
result this session did not take on trust: the earlier **summary/text_stale audit** (see below)
independently re-verified every quantitative claim in every `summary` field against `notes.md`
and found the batch's counts, ranges and quotations hold up.

## Blind checks

`SKILL.md` requires a blind raw-evidence re-derivation on at least one issue per batch, and
always on every issue whose suggested action is `close-fixed` — the highest-stakes verdict,
since it is the one most likely to be acted on without re-checking. This batch has seven.

All seven close-fixed issues (`#4965`, `#5080`, `#5261`, `#5563`, `#5587`, `#5681`, `#5748`)
were reported to this collation session as having passed a blind re-derivation performed by
gpt-5.3-codex, and this session incorporates that report rather than re-running the exercise
itself. **Only one of the seven has an on-disk trace of that specific check**, and this is
recorded plainly rather than papered over: `#5261/method-notes.md` documents that a fresh
general-purpose agent, given only the raw evidence (repro, `cmd.txt`, `match.json`, every
`out-*.txt`/`variant-*.txt` capture, the Compiler Explorer artifacts) with `notes.md`,
`verdict.json` and `comment.md` withheld, independently reproduced the same status, the same
non-monotonic history and both of its transition boundaries, the same invalid-probe releases,
the same `complete` repro-quality call, and the same `close-fixed` recommendation — and,
unprompted, flagged the same two open gaps this triage already recorded (the fix commit is not
pinned to one line, and the historical Debug-build assert is corroborated only by the
maintainer's 2023 comment, not independently reproduced here). The other six close-fixed
issues' directories carry no comparable artifact naming a blind pass, its inputs, or its
findings.

This session independently deep-read the full `notes.md`, `comment.md` and (where present)
`method-notes.md` for **all seven** close-fixed issues rather than accepting the blind-check
report as a substitute for that reading — see **Per-issue findings** above for what that
review found. Every one of the seven holds up: a `complete` repro reproduced verbatim from the
filed source, a positive and negative control, an honestly-hedged commit attribution, and (for
five of the seven) a real invalid-probe or DCE-hiding-the-question correction that a naive
reading of the raw bisect output would have missed. The evidentiary gap is specifically about
the *blind-check artifact's own documentation*, not about the underlying verdicts, which this
session verified by an independent route (direct reading, plus the cross-issue corroboration in
`#5261`/`#5681` sharing a fix commit, plus the corrected release-level scoring `reindex`
produced for `#5080`). Recorded as a completeness gap for whichever session or tooling change
next standardises how a step-10/blind-check pass leaves its own trace on disk, consistent with
`SKILL.md`'s own principle that a check with no trace on disk is one nobody can later tell was
performed.

## Timeline check

Every one of the 100 batch issues' GitHub timelines was fetched read-only
(`gh api repos/microsoft/DirectXShaderCompiler/issues/<N>/timeline`) and filtered to
`cross-referenced` events. **100/100 issues checked, zero errors, zero events created by this
triage.** 56 issues have no cross-reference at all; the other 44 carry 81 pre-existing events
between them, every one attributable to a real project contributor or maintainer
(`llvm-beanz`, `pow2clk`, `damyanp`, `python3kgae`, `tex3d`, `elasota`, `hekota`,
`devshgraphicsprogramming`, `Keenuts`, `MarijnS95`, and others) referencing ordinary issues,
PRs, or related repositories (`llvm/llvm-project`, `microsoft/hlsl-specs`,
`Traverse-Research/hassle-rs`, `KhronosGroup/SPIRV-Cross`, and similar) — including several
dated within days of this triage session (e.g. `#4805`'s 2026-08-15 cross-reference from
`#8781`, `#5079`'s 2026-05-08 reference from PR #8431), all of which are ordinary,
independently-verifiable project activity unconnected to this batch. No event's actor,
timestamp, or source repository matches this triage's own branch, commit history, or session
identity. This batch's own commit(s), when made, will use bare issue numbers exactly as
`SKILL.md` requires — nothing in this session posted, edited, labelled, closed or reacted to
anything on GitHub, and no commit referencing an issue number by `#`/`GH-`/URL syntax was made.

## Summary/`text_stale` audit

Per `SKILL.md`'s explicit instruction to re-read every `summary` and `text_stale` field
against `notes.md`, sentence by sentence, as a deliberately separate pass — compression must
only remove claims, never add one — **all 100 issues were checked twice**, by two independent
full passes covering the batch in two halves, and every flagged concern was then personally
re-verified by this session against the primary evidence rather than accepted on the auditor's
word.

Five concerns were raised; all five resolved as non-issues on inspection, which is itself worth
recording precisely rather than only asserting a clean result:

- **`#5768`** — flagged for a supposed "20 probeable releases" vs. an alleged "18 reproducing +
  2 invalid-probe" split in `notes.md`. On inspection, `notes.md` states no such split for this
  issue; the quoted contradicting text does not appear anywhere in `#5768`'s own directory. The
  summary's "all 20 probeable stable releases" is exactly what `notes.md` itself says. **False
  positive** — a misattributed quote, not a real discrepancy.
- **`#6084`** — flagged for "no GitHub Actions workflow builds DXC either" reading stronger
  than `notes.md`'s "the three workflows … none of which build DXC." These are the same claim;
  `notes.md` enumerates all three existing workflows by name and states none builds DXC, which
  is exactly what the summary restates. **False positive.**
- **`#5389`** — flagged for stating "`-HV 2021` does NOT fix it" without carrying forward a
  narrower, separately-flagged Debug/Release discrepancy on one *sub*-case (a scalar `.x`
  variant). `notes.md` itself frames that sub-finding as explicitly **not affecting the
  headline verdict** and as a side check of a different maintainer claim, not part of the
  primary reported defect the summary describes. **Not an omission** — the summary is scoped to
  what it claims, correctly.
- **`#5448`** — flagged for stating a duplicate-diagnostic consequence more definitely than the
  evidence supports. The same summary field already carries the caveat, in its own next
  sentence, that reaching this code path needs hand-authored DXIL through the standalone `dxv`
  validator, which was not built or run here. **Not a violation** — the caveat is present in
  the same field, not omitted.
- **`#5674`** — the one genuine, if minor, finding: the summary's "using it in an expression"
  is a touch broader than what was actually measured (the identifier used specifically as an
  operand of the `*` operator, per `notes.md`'s own repro and crash-site analysis in
  `Sema::CreateOverloadedBinOp`). This does not change the verdict, history, or suggested
  action — the regression boundary and attribution are unaffected — but it is a real instance
  of the compression risk `SKILL.md` warns about, recorded here since the two-pass audit exists
  precisely to catch this class of thing even when it does not move a verdict.

No `text_stale` field was found describing mere severity-understatement rather than genuine
staleness (the specific #8737-shaped failure mode `SKILL.md` warns against); every one of the
9 flagged issues names a concrete mismatch between the issue's own standing text and a directly
measured current behaviour. See **Per-issue findings** for what each says.

## `match*.json` predicate audit

All 88 `match*.json` files across the batch were read in full and each `note` field checked
against its own `kind`/`value` structure — the specific check `SKILL.md` calls out, since a
predicate's prose explanation is unreviewed and has been wrong while the predicate itself was
right. **No discrepancy was found in any of the 88.** Every composed predicate's note correctly
describes its actual clauses (`all_of`/`any_of` membership, which clause is the positive
anchor vs. the absence signal, which clauses exist purely as anti-vacuity guards), every
claimed control is present as a named file with an `--expect` this session could trace back to
a real capture, and every claim about why a given `kind` was chosen (`internal_failure` vs. a
text `contains`, a structural regex vs. a literal string) matches the reasoning already
required by step 4. This is a stronger result than "no note lied about its predicate" — the
notes in this batch are, without exception, a reliable second source for the predicate's own
reasoning, not merely non-contradictory prose sitting next to it.

## Existing-issue refresh

Separately from batch-019's own 100 issues, the user requested a freshness check of the **107
previously-triaged issues** from batches 1–18 (the remaining 207 − 100 = 107): each was
re-fetched read-only for current metadata and comments — **no compiler was rerun, and no
verdict, `notes.md` or `comment.md` from any earlier batch was touched.** This section reports
what changed since each was originally triaged; it makes no claim about whether any earlier
verdict is still current, since that would require re-running the compiler, which this refresh
explicitly did not do.

**Seven of the 107 changed.** Three are Unicode-normalisation only, with no content change:

- **`#2128`** — one apostrophe in the issue body was corrected from a double-encoded mojibake
  form to the correct single `’` (U+2019) codepoint. Verified character-by-character (`ord()`
  on the decoded string, not by printing it — the Windows console's active codepage cannot
  render curly punctuation and produces its own misleading-looking substitution on *display*
  that has nothing to do with the underlying data; every claim in this section was checked by
  codepoint, not by eye).
- **`#2427`** and **`#3092`** — one comment each has an apostrophe or an emoji corrected the
  same way (`#2427`: an 😲 emoji restored from a four-character double-encoded mojibake
  sequence; `#3092`: another apostrophe). No other byte differs in either issue's body or any
  other comment.

Four are substantive and worth a maintainer's attention:

- **`#3150`** ("Unspecified behavior from new-to-DXIL sdiv instruction") — gained a maintainer
  decision comment (damyanp, 2026-08-17): *"we're going to continue with option 1 ('keep the
  existing behavior') for the foreseeable future unless a compelling reason to change direction
  arises, and ensure that SM 7.0 doesn't end up in this situation."* This settles the design
  question the thread had been debating (comments went 14 → 15); the issue itself remains open
  with the `docs` label, consistent with the earlier plan to document the behaviour rather than
  change it.
- **`#7033`** ("[SPIR-V] Ray queries do not work with -fspv-debug=vulkan-with-source") —
  **state changed OPEN → CLOSED**, with a new closing comment (damyanp, 2026-08-19): *"It looks
  like https://github.com/microsoft/DirectXShaderCompiler/pull/7139 fixed this, but it didn't
  tag the issue with 'Fixed' and so it wasn't closed when it merged."* This issue was
  independently triaged as `close-fixed` in batch-018 (fixed at v1.9.2602) before this maintainer
  action; the two now agree, and PR #7139 is a fix candidate this triage session did not itself
  attribute.
- **`#8732`** ("[SPIR-V] SPV_EXT_descriptor_heap mixed bound/heap aliasing causes silent
  miscompilation or ICE") — the **`needs-triage` label was removed**, leaving `bug, spirv`. The
  body also differs by exactly one character (an en-dash mojibake-corrected the same way as
  `#2128`/`#2427`/`#3092` above — confirmed by direct codepoint diff, the *only* difference in
  a 7500-character body); that part is cosmetic, not the substantive change. The label removal
  is the real signal: it indicates a maintainer has looked at the report since it was filed.
- **`#8737`** ("Atomics on RWTexture2DMS result in silent UB or ICE") — **gained three
  comments** (0 → 3). These are the historically significant ones: they are the reporter
  correction and maintainer apology `SKILL.md`'s own Hard Rules section already documents as
  the real-world incident behind the "never write an issue reference into a commit message"
  rule. The reporter (`Maraneshi`) wrote: *"It seems like some LLM has triaged this and made a
  comment that seems like half a suggestion and half a misunderstanding … Just the sentence
  about the sample index was weird/wrong."* The maintainer (`damyanp`) replied: *"sorry for the
  noise. I'm experimenting with some auto-triaging tooling and although it's all meant to be
  done in my fork and not post anything, it tagged the issue in a commit message which is what
  showed up for you here."* This refresh is the first time that resolution has been captured on
  disk in this skill's own data; it is presented here as historical record, not as something
  this session caused or needs to act on.

**Distinguishing the two categories matters.** `#2128`/`#2427`/`#3092` and the cosmetic half of
`#8732` are pure data-hygiene artifacts with zero bearing on any verdict. `#3150`, `#7033`,
`#8732`'s label, and `#8737` are real discussion/state changes that a maintainer scanning
`overview.md` should know about even though **no compiler measurement for any of these seven
was refreshed** — their original verdicts (from batches 3, 18, and other earlier batches) stand
as previously recorded, and this section does not revise, supersede, or re-derive any of them.

`issue.json` is fetched GitHub metadata, not a compiler-output capture — refreshing it is what
`fetch` always does, not a special exception to the rule against hand-editing a measurement.
The one thing worth flagging precisely: the repository's own `data/issues/<n>/issue.json` for
these seven now holds the *refreshed* metadata rather than the snapshot each was originally
triaged against, so a reader who wants the exact body/comment text an earlier verdict quoted
verbatim needs the prior snapshot (preserved outside this repository at refresh time), not the
current file. This session did not perform, undo, or extend that refresh, and made no further
edit to any of the seven beyond reading them for this report.

## Evidence verification

- **`reindex`** (run twice this session: once after each shared-code change, and once as a
  final confirmation) rebuilds `triage.db` from every committed `verdict.json` and re-scores
  every archived probe against today's predicate code. Final state: **207 issues, 3096 runs,
  every probe re-scores as captured, none are stale, and no issue is missing required
  evidence.** The one disagreement `reindex` found after the `UNSUPPORTED_MARKER_RE` change —
  `#5080` v1.6.2112: `no-repro` -> `invalid-probe` — is exactly the expected, already-understood
  correction described under **Method lessons** item 6 and in `#5080`'s own `notes.md`/
  `method-notes.md`; it was investigated (not merely accepted blind), confirmed correct, and
  restamped with `reindex --accept`, which touches only the capture's `# verdict:`/
  `# invalid-probe-reason:` header lines, never a measurement. No other issue in the 207-issue
  tree was affected by either shared-code change this session made (the `--linear` result
  labelling and the stale-output-file scratch-clearing fix are both about *how a probe runs or
  is reported*, not about how existing captured text is classified, so they could not and did
  not change any other issue's re-scoring).
- **`render_comments.py 019`** spliced all 100 `comment.md` drafts into this report; re-run
  after every edit to any of them, per the standing rule that the report and the artifacts must
  not drift apart.
- **`render_overview.py`** regenerated `reports/overview.md` from `triage.db` after the above:
  **207 issues across 19 batches** (001–019), tiers `close-fixed=16, duplicate=1,
  enhancement-not-bug=30, needs-human-judgement=23, needs-repro-from-reporter=2,
  still-valid-keep-open=135`. Generated, not hand-edited, as required.
- **`triage.py audit --collated`**: `no missing evidence in 207 issue(s)`.
- **`test_predicates.py`**: **all predicate tests passed**, including the 8 new assertions this
  session added (2 for the `#5704` scratch-clearing fix's `_run_probe_command_list` behaviour —
  a fake two-release sweep that reproduces the exact byte-identical-stale-read signature
  without the fix and does not with it; 6 for `describe_linear_result`'s single-transition vs.
  genuinely-non-monotonic distinction) and the 2 new assertions for the `#5080`/SPIR-V
  target-environment marker (a positive case and an anti-over-match negative control). The
  suite's own internal `check_paths.py` gate reports `7959 committable text files; 16
  allowlisted matches in 4 files; no unexpected machine paths`.
- **`check_paths.py`**, run directly: identical clean result. This report file itself was
  scanned and introduced no new leak.
- **Git-status scope check**: every modification and every new file this batch produced is
  inside `.github/skills/dxc-issue-triage/` — the 100 new `data/issues/<nnnn>/` directories, the
  7 refreshed `issue.json` files (pre-existing from the refresh described above, not touched
  further by this session), the `SKILL.md`/`scripts/triage.py`/`scripts/test_predicates.py`
  edits described in this report, and `data/reports/batch-019.md`/`overview.md`. Two stray
  artifacts were found and removed as cleanup, not left behind: `issue5309_raw.json` (a
  duplicate, slightly-earlier partial fetch of `#5309`'s own `issue.json`, missing only the
  `state` field — redundant scratch, not evidence) sitting directly under the skill root rather
  than inside `data/issues/5309/`, and a 0-byte `err.txt` at the repository root, outside the
  skill tree entirely, predating this session. **No DXC source file changed. No commit was
  made.**

## Limitations

- **Age-slice sampling bias** (restated from the top): every verdict here is about a shader
  compiler behaviour that has had, in most cases, roughly three years to move since filing.
  Nothing in this batch supports a claim about the shape of the *current* (2024–2026-filed)
  backlog.
- **Seven commit-level attributions are unbuilt.** Every `close-fixed`/`changed-behavior`
  verdict names a release-level fix boundary measured directly; where a specific commit is
  named, it is a candidate identified by window-narrowing and diff reading, explicitly not
  confirmed by building it and its parent in isolation, per this task's no-rebuild-of-any-shared-
  or-per-issue-target constraint.
- **Six of the seven close-fixed issues' blind checks have no on-disk trace of their own
  process**, only this collation session's incorporation of a reported outcome — see **Blind
  checks** for exactly what is and is not independently verifiable from disk today.
- **The `#5704` tooling fix was scope-checked against every multi-line `cmd.txt` in the current
  207-issue tree, not against every issue this skill will ever triage.** A future multi-line
  pipeline is protected going forward; nothing about this fix retroactively re-examines a
  single-line `cmd.txt` issue for an unrelated class of staleness.
- **The existing-issue refresh covered metadata and comments only.** No compiler was rerun for
  any of the 107 issues; a "does this still reproduce" claim for any of them would need a fresh
  triage pass, not this refresh.
- **This report was authored by a single collation session** briefed only by what could be
  reconstructed from `data/issues/<nnnn>/`, the four external step-10 review logs, and the
  external refresh snapshots named in this batch's brief — not by any other session's summary,
  worker self-report, or memory of prior batches.

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


### Draft — [#4766](https://github.com/microsoft/DirectXShaderCompiler/issues/4766) How can I build `dxil` and `dxcompiler` as a static library?

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4766](https://github.com/microsoft/DirectXShaderCompiler/issues/4766).

Still an open, unactioned ask as of `main` (`89e2f98e2`).

`tools/clang/tools/dxcompiler/CMakeLists.txt` still hardcodes
`add_clang_library(dxcompiler SHARED ${SOURCES})` — the exact line @MarijnS95 linked in 2023.
That line dates to the repository's first commit (`6ee4074a4`, 2016-12-28) and has never been
touched since; the file's most recent change (`6ea7cf1c1`, #8166) is an unrelated MacOS warning
fix. `llvm_add_library` (`cmake/modules/AddLLVM.cmake`) already supports a `STATIC` target, but
nobody has made the change. `dxildll` (`dxil.dll`) has the identical pattern: it only entered
this repo via #6866 (2024-09-05, after this issue was filed) and hardcodes `SHARED` too,
unchanged since.

#5985 cites this issue and discusses moving `DllMain`'s work (including its `LoadLibraryA` call
for `dxil.dll`) into `DxcCreateInstance`, which @amaiorano described there as non-trivial and
untaken. `include/dxc/Support/dxcapi.use.h` still calls `LoadLibraryA` from `DllMain` today.
Both issues remain open with no linked PR.

No shader or `dxc` invocation applies here; this is a CMake configuration question, so no CE
link or release history is included.

Suggest adding `enhancement` alongside the existing `build`/`api` labels, since the thread
converged on a specific, still-open feature ask rather than only an unanswered question.

---
<sub>Triaged with AI assistance from `git log`/`git show` evidence in this repository, not a
compiler run; please flag anything that looks wrong.</sub>
````

### Draft — [#4786](https://github.com/microsoft/DirectXShaderCompiler/issues/4786) `DxbcConverter` can corrupt integer Immediate Constant Buffer values (x86)

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4786](https://github.com/microsoft/DirectXShaderCompiler/issues/4786).

Still reproduces on `main` (measured against commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).
This is a regression, not a standing bug — and it's been broken for over three years.

## What's still there

`projects/dxilconv/lib/DxbcConverter/DxbcConverter.cpp` still builds the `"dx.icb"` global with
`ArrayRef<float>((float *)Inst.m_CustomData.pData, Size)`, and
`lib/Bitcode/Writer/BitcodeWriter.cpp` still round-trips each element through
`getElementAsFloat()` (returned by value) and a `union{float;uint32_t;}` bit-cast — the exact
two-hop reinterpret this issue describes, unchanged.

## History

- PR #4790 (this issue's own fix) merged 2022-11-23, first shipped in `v1.7.2212`.
- PR #5253 reverted it on a release branch, and PR #5279 reverted it on `main` too (merged
  2023-06-08), "to be re-evaluated once AMD root-causes the issue and updates the drivers." No
  re-fix has landed since — every stable release from `v1.7.2308` (2023-08-14) through the
  current `v1.9.2607` still has the `float`-cast version, matching `main`.

So the fix window was `v1.7.2212`–`v1.7.2212.1` only (roughly Dec 2022–Aug 2023); everything
before and everything since is broken.

## Mechanism, confirmed on this machine

The x86-vs-x64 ABI difference this issue attributes the corruption to is directly
reproducible: a minimal function that reads `0xffbfffca`, bit-casts it to `float`, and returns
it by value produces `0xffffffca` when compiled for x86 (matching this issue's reported bit
flip exactly) and is unchanged when compiled for x64, with the same MSVC toolchain. Two extra
canonical signalling NaNs corrupt the same way on x86; two non-NaN controls are unaffected on
both architectures.

## What I couldn't test directly

`dxc.exe`'s own HLSL pipeline never calls `DxbcConverter` (it only converts legacy DXBC, via
the D3D12 runtime or a standalone `dxbc2dxil`), and this checkout doesn't build `dxilconv`, so
I couldn't run the reporter's DXBC through the converter end-to-end here. I also can't
independently confirm the separate WARP-side fix @jenatali mentioned (that's about WARP
accepting integer-typed `"dx.icb"`, a different claim from whether the corruption itself is
gone). @ben-clayton's 2023-09-06 reopen request is accurate and the issue is still open.

## Suggested labels

Keep `dxilconv`; add `bug` and `correctness` — this is a currently-reproducing data-corruption
defect, not just a subsystem tag.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4792](https://github.com/microsoft/DirectXShaderCompiler/issues/4792) `libdxcompiler.so` locks up when used in many threads at once

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4792](https://github.com/microsoft/DirectXShaderCompiler/issues/4792).

Still reproduces on `main` (verified against a Debug build at
89e2f98e29c289ae8ad9e00dd310104fea9fd7df) — not because a hang was reproduced in this
session, but because the racy code you found is unchanged:

```
$ git log --oneline --all -- include/llvm/PassSupport.h
f805233b4 Revert license text in banner comments to original llvm verbage (#33)
6ee4074a4 first commit
```

`CALL_ONCE_INITIALIZATION` has never been touched since the repo's first commit. #4818, which
would have applied the `static`-initializer fix from D19271 you mentioned, is still closed
and unmerged.

Worth reading the full #4818 thread if you haven't: after that PR opened, @llvm-beanz talked
through it with you in real time, and by the end of it your `std::call_once` port had *also*
locked up — this time inside libstdc++'s `__cxa_guard_acquire`, on a different pass
(`TargetTransformInfoWrapperPass`) — and a ThreadSanitizer run on DXC turned up several
unrelated data races (`ManagedStatic`, `MutexImpl::acquire`, `Sema`'s implicit special-member
declaration, one heap-use-after-free). Nobody in that thread claims the concurrency problem
was actually solved; it reads like it was still open when the PR was closed for inactivity.

I built a small multithreaded harness that loads `dxcompiler.dll` and fires many threads at
`IDxcCompiler3::Compile` from a shared barrier, to try to reproduce the hang directly. Across
13 attempts (8 through 512 threads, up to 512 all racing the same cold-start compile at once),
it did not hang on this Windows/MSVC Debug build. That's a bounded negative result on one
platform, not a "fixed" — your two stack traces are both inside Linux/glibc-specific
primitives (`__gthread_once`, `__cxa_guard_acquire`) with no direct Windows equivalent in this
call path, so a clean Windows run doesn't say much about the Linux behavior you and
@llvm-beanz were chasing.

Given the source is unchanged and the fix discussion stalled without a resolution, this looks
like it should stay open rather than close. Adding `bug` and `api` labels since there
currently are none on the issue.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4805](https://github.com/microsoft/DirectXShaderCompiler/issues/4805) Compiler does not use the custom include handler when compiling with `-Zi`

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4805](https://github.com/microsoft/DirectXShaderCompiler/issues/4805).

The core report — a custom `IDxcIncludeHandler`'s content is not what ends up
embedded as an included file's SPIR-V debug source — still reproduces today
on `main` (`89e2f98e2`). The specific 2022 crash does not reproduce as
originally described, and a different, more severe failure mode was found
during this triage that the original report did not describe.

## What's confirmed

A minimal custom `IDxcIncludeHandler` that serves one `#include` purely from
memory (no matching file on disk at all — the reported scenario) compiles
successfully, but the resulting container carries **no trace** of the
handler's content for that file's `DebugSource`. This isolates to
`EmitVisitor.cpp`'s `ReadSourceCode`, which does its own independent raw disk
read for debug-source text rather than reusing the buffer the supplied
include handler already returned to the parser — there is no fallback path to
the handler's content anywhere in that file.

A positive control (a real on-disk file byte-identical to what the handler
serves) does show the marker present, confirming the harness and the API path
both work, and that the reported case's absence is a real finding.

## The crash from 2022

Not reproduced. The disk-read failure has been wrapped in a `catch (...)`
since 2020 (predating this issue), and no build tested — including the
release current when this was filed — crashes on the reported scenario; it
compiles cleanly with the include's content silently missing from debug info.
This matches [@leozzyzheng's comment](https://github.com/microsoft/DirectXShaderCompiler/issues/4805#issuecomment-3552522826)
more closely than the original report: "ignored," not "crashes."

## A newly-found, worse failure mode

If a file happens to exist on disk at the resolved include path but with
*different* text than what the handler actually served (plausible for anyone
layering a custom handler over an otherwise-normal project tree — exactly the
use case described in this issue), the compile now **fails outright**:

```
fatal error: generated SPIR-V is invalid: NonSemantic.Shader.DebugInfo.100
DebugTypeMember: operand Column End (41) is larger then Line 3 column length
of 2 found in the DebugSource text
```

This does not happen on the release current when this issue was filed
(v1.7.2207) or as late as v1.8.2502 (2025-02) — only on `main`. The boundary
brackets PR #7662 (`97b5edbc4`, merged 2025-07-24, "Fix DebugSource for files
which are not found"), which narrowed a fallback that previously (silently,
incorrectly) substituted the *main file's* text for any file whose raw
disk-read failed. The narrowing looks correct in isolation, but it changed
this case from a quiet wrong-content substitution into a hard compile
failure.

## Suggestion

`ReadSourceCode` in `tools/clang/lib/SPIRV/EmitVisitor.cpp` needs to consult
the buffer the caller's `IDxcIncludeHandler` already supplied during parsing
for an included file's debug-source text, instead of (or before) doing its
own independent disk read. `debug info` might be worth adding alongside the
existing `bug`/`api` labels, since this is squarely a debug-info generation
defect.

Compiler Explorer was not used: its `dxc` panes can only drive `dxc.exe`'s own
disk-backed default include handler, so there is no way to exercise a
caller-supplied `IDxcIncludeHandler` through CE at all.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4858](https://github.com/microsoft/DirectXShaderCompiler/issues/4858) [DXIL] Illegal code motion for CalculateLevelOfDetailUnclamped

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#4858](https://github.com/microsoft/DirectXShaderCompiler/issues/4858).

Still reproduces on `main` (1.9.0.5465, `89e2f98e2`), and in every stable release from v1.4.1907
through v1.9.2607 — this has never once compiled correctly. (The local build's `--version`
self-reports a fork-local `7665270b9`; its source has been verified identical to public
`89e2f98e2` outside this repo's triage-skill directory, which is the commit cited here.)

Repro (verbatim from the issue): https://godbolt.org/z/1h4fff5Ef — both `dxc_1_6_2112` and
`dxc_trunk` place the `CalculateLOD` op inside the block reached only by the branch's true arm,
even though the source computes it unconditionally before that branch:

```
br i1 %3, label %4, label %10
; ...
%4:
  %5 = call float @dx.op.calculateLOD.f32(...)
```

The second (`sin(uv)`) repro from the comments reproduces identically locally.

`-Od` (disable optimizations) suppresses it — the `CalculateLOD` call then stays in the
unconditional entry block, before the branch — which is what let us build a control confirming
the finding is about this specific code motion and not an artifact of the check.

**`check-in-clang` is still open, not answered.** The new Clang HLSL front end can't be compared
yet: it rejects this shader before reaching codegen, with `use of undeclared identifier
'InterlockedMin'` — a missing, unrelated front-end feature, not a verdict on the sinking.

No label changes suggested; `bug`, `correctness` and `check-in-clang` all still describe this
accurately.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4871](https://github.com/microsoft/DirectXShaderCompiler/issues/4871) When using "--variable" as an argument to an inout function, 2 is subtracted not one

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4871](https://github.com/microsoft/DirectXShaderCompiler/issues/4871).

Still reproduces on `main` (public commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
Debug build; `dxc --version` self-reports fork-local build id `7665270b9`).
`Func(--i)` — an empty `inout` function called with a pre-decremented argument —
still lowers to a subtraction of 2 rather than 1:

```
$ dxc -T ps_6_0 -E PSMain -Zi -Qembed_debug repro.hlsl
  %dec1 = add i32 %0, -2, !dbg !38 ; line:7 col:10
```

Controls isolate exactly where the extra subtraction comes from: neither an
`inout` call by itself, nor a pre-decrement by itself, produces it — only a
decrement/increment expression written *directly* as the `inout` argument
does. That matches the copy-in/copy-out semantics `inout` currently has at
the AST level.

History (20 stable releases, v1.4.1907–v1.9.2607, linear scan): clean at
v1.4.1907, reproduces at every release from **v1.5.2010** onward with no
reversion — a genuine, still-open regression, not something that was always
broken.

One update since the last comment here: the fix path named above (`#5377`
"out and inout should always be references") was closed `not planned` in
September 2024, and the draft PR it points to (`#5249`) is still open and
unmerged — so that rewrite never reached `main`, consistent with every probe
above still reproducing. Separately, though, Compiler Explorer's
`hlsl_clang_trunk` — the new Clang-based HLSL front end DXC's HLSL support is
migrating to — already gets this exact case right (`add i32 ..., -1`, used
once). Compiler Explorer link (compute-shader restatement, since the new
front end can't yet lower a pixel shader returning `SV_Target` as `uint`):
https://godbolt.org/z/4318d6hbY

Suggested labels: keep `bug`, add `correctness` (this is a silent
shader-correctness miscompile, not a diagnostic or crash issue).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4888](https://github.com/microsoft/DirectXShaderCompiler/issues/4888) Dynamic resources validation errors: All metadata must be used by dxil.!55 = !{i32 1}

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4888](https://github.com/microsoft/DirectXShaderCompiler/issues/4888).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`): compiling the
shader above with `-T ps_6_6 -E PSMain` still fails DXIL validation with the same class of
error, only the metadata slot number differs from the original report:

```
error: validation errors
error: All metadata must be used by dxil.!21 = !{i32 1}
Validation failed.
```

This has been true on every stable release checkable back to v1.6.2104 (2021-04-20, the oldest
release that even accepts `-T ps_6_6`) — every one of them fails the same way, so this has
never worked. [Compiler Explorer](https://godbolt.org/z/fhjbK7r4x) confirms the same error on
today's `dxc_trunk` and on CE's oldest DXC (1.6.2112), using a compute-shader restatement of the
same pattern (the pixel-shader repro's stage isn't relevant to the defect).

@tex3d's comment above is still the best statement of what's going on: `dxc` doesn't legalize a
static array of `ResourceDescriptorHeap`-backed resource *objects* indexed by
`NonUniformResourceIndex`, and per that comment the intended fix is a proper diagnostic naming
the unsupported pattern, not (yet) making the code legal. That diagnostic hasn't landed — the
compiler still surfaces the internal validator's generic complaint instead.

One thing has changed since 2023: @Keenuts' separate report that adding `-spirv` crashes with an
`isa<>` assertion no longer reproduces. It crashed on every stable release through v1.8.2403.2
(2024-03-29) and stopped crashing at v1.8.2405 (2024-05-24) onward, where it now fails with an
ordinary diagnosed error instead (currently `error: Cannot cast initializer type
'Texture2D<vector<float, 4> >' into variable type 'const Texture2D<vector<float, 4> >'`). Worth
noting so nobody re-files a redundant crash report against that specific symptom.

Suggested label: add `diagnostic`, alongside the existing `bug` — this is exactly the "add a
diagnostic for the unsupported pattern" work tex3d described.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

### Draft — [#4914](https://github.com/microsoft/DirectXShaderCompiler/issues/4914) [feature request] Copying "this" fails

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4914](https://github.com/microsoft/DirectXShaderCompiler/issues/4914).

Still reproduces on `main` (public upstream commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
Debug build) and on every stable release checked, v1.4.1907 (2019-07) through v1.9.2607
(2026-07-29) — the full checkable release history, three and a half years before this report:

```hlsl
struct S {
    int value;
    S getThis() { return this; }
    void copyThisInto(out S dst) { dst = this; }
};
```

```
error: cannot compile this aggregate expression yet
        return this;
               ^~~~
```

The gap is narrow and CodeGen-specific, not a language/design limitation: Sema already accepts
this without complaint (see the currently-passing `-fsyntax-only` test
`tools/clang/test/HLSL/cpp-errors.hlsl:563`, `CInternal getSelf() { return this; }`, no
`expected-error` attached). `HLSLExternalSource`/`genereateHLSLThis` gives `this` value-type
semantics (an lvalue of type `S`, not `S*`), so returning or assigning `this` by value is an
aggregate expression — and `AggExprEmitter` in `CGExprAgg.cpp` has no `VisitCXXThisExpr`
override (unlike the scalar emitter), so it falls into the generic
`"cannot compile this %0 yet"` diagnostic. `this.member` access is unaffected (confirmed with a
same-shape control) because it never reaches the aggregate emitter as a bare `this`.

This is also DXIL-specific: the identical `repro.hlsl`, same command plus `-spirv`, compiles
cleanly and folds correctly — confirming @Keenuts's comment above by re-running it directly.
FXC also compiles the identical struct/member-function shape cleanly. The new Clang-based HLSL
front end (`hlsl_clang_trunk`) reproduces the byte-identical diagnostic, so the gap is not
DXC-legacy-only. [Compiler Explorer: FXC succeeds, `dxc_1_6_2112`/`dxc_trunk`/`hlsl_clang_trunk`
all fail identically](https://godbolt.org/z/jbqesq9P1).

Given that two independent compilers/backends already treat "copy the whole `this`" as ordinary
code, this reads more like an unimplemented single CodeGen visitor than an open design question.
Suggest adding `bug` alongside the existing `enhancement`/`question`/`dxil`/`fxc-disagrees`
labels; leaving `question` in place since it does capture the original, reasonable "should this
even be supported" concern raised when this was filed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4958](https://github.com/microsoft/DirectXShaderCompiler/issues/4958) Compiling hull shader with unused globals causes internal compiler error

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4958](https://github.com/microsoft/DirectXShaderCompiler/issues/4958).

Still reproduces on `main` (Debug build at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):

```
$ dxc -T hs_6_6 -E mainHS -Fo output.dxil repro.hlsl
Internal compiler error: LLVM Assert
```

The trapped assert is:

```
assert(Index < Length && "Invalid index!")
llvm::ArrayRef<class llvm::Value *>::operator []
```
called from `StoreVectorOrStructArray`, inside HLSL's SROA pass
(`SROA_Helper::RewriteForStore`) — matching @Keenuts' comment exactly: the pass is rewriting a
store into `gProjTextureMaps` before that global is eliminated as dead. Continuing execution
past the trap (as an `NDEBUG`/Release build would) hits an access violation in the same call
chain, so this is one defect, not two.

Bisecting stable releases: `v1.6.2104` compiles this cleanly; `v1.6.2106` is the first release
that crashes, with the exact stderr and address the original report quotes
(`Internal compiler error: access violation. Attempted to read from address
0xFFFFFFFFFFFFFFFF`). It has reproduced in every release since — including the newest
catalogued stable build, `v1.9.2607` — and on Compiler Explorer's `dxc_trunk`
(`error: cast<X>() argument of incompatible type!`, the same underlying internal-failure class
reported through a different build configuration). [Compiler Explorer
repro](https://godbolt.org/z/zdcvTzcd7) (older DXC + trunk). Confirmed DXIL-only — the identical
shader compiled with `-spirv` succeeds, matching @Keenuts' comment.

One correction to the original report: re-testing `ARRAY_SIZE` today, only `0` (an empty
array) compiles cleanly — `2`, which the report says "appears to succeed", crashes on current
`main` just like `1`, `3` and `5` do. The bug looks slightly broader than originally described,
not narrower.

Existing labels (`bug`, `dxil`, `crash`) already look correct; no changes suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#4965](https://github.com/microsoft/DirectXShaderCompiler/issues/4965) int f(int) as /E results in "Internal compiler error: access violation. Attempted to read from address 0x0000000000000018"

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4965](https://github.com/microsoft/DirectXShaderCompiler/issues/4965).

This no longer reproduces on `main` (built at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).
Compiling the filed source with `-T ps_6_2 -E f` now gives a clean diagnostic instead of any
internal failure:

```
repro.hlsl:1:1: error: recursive functions are not allowed: function 'f' calls recursive function 'f'
repro.hlsl:1:1: note: recursive function located here:
```

`-E f` makes `f` the entry point, and the source also calls `f` at global scope to initialize
`static int b`. DXC synthesizes calls to global initializers inside the entry-point wrapper it
builds for `f`, so `f`'s own wrapper ends up calling `f` — a genuine self-recursion introduced
by entry-point lowering. The existing recursion check now catches that before codegen runs,
which is why the Debug-build SROA assert reported in this thread
(`otherwise we flattened a library function.`) no longer fires: the compile never reaches that
pass.

A stable-release bisection puts the fix at **v1.8.2505** (last reproducing release: v1.8.2502).
Every stable release from v1.4.1907 through v1.8.2502 does fail internally, matching all of the
symptoms reported in this thread across that time span — a silent access violation, a printed
`Internal compiler error: access violation`, and the `llvm::cast<X>() argument of incompatible
type!` message — depending on release and build configuration. The window between v1.8.2502
and v1.8.2505 is 162 commits; no individual fixing commit was identified.

[Compiler Explorer](https://godbolt.org/z/ee6xoP8jz): CE's oldest DXC (`1.6.2112`, Linux
Release) terminates with `SIGSEGV`, and `dxc_trunk` shows the same diagnostic as above —
corroborating both the old crash and the current fix on a second platform.

Suggested labels: add `crash` (this was a crash/assert issue for its whole open lifetime,
which the current label set doesn't capture); no other changes.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5039](https://github.com/microsoft/DirectXShaderCompiler/issues/5039) Nonsensical error message when using undef offset in structured buffer

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5039](https://github.com/microsoft/DirectXShaderCompiler/issues/5039).

Still reproduces on `main` (public commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df);
the local build self-reports a different, fork-local commit,
`1.9.0.5465 (triage, 7665270b9)`, but its source tree is identical to
`89e2f98e2`), and on every stable release checked, v1.4.1907 through
v1.9.2607. This has never been fixed — only reworded.

**Compiler Explorer:** https://godbolt.org/z/aM54EnbzT

```
$ dxc -T ps_6_0 repro.hlsl
error: llvm::cast<X>() argument of incompatible type!
```

That matches the text quoted in the report on current builds. The wording
*has* drifted twice over the compiler's history, but
neither change is a fix and neither reaches the requested message:

| releases | wording |
| --- | --- |
| v1.4.1907 – v1.5.2010 | access violation (crash), no diagnostic text |
| v1.6.2104 | access violation with internal-error text |
| v1.6.2106 – v1.6.2112 | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` |
| v1.7.2207 – v1.9.2607, `main` | `error: llvm::cast<X>() argument of incompatible type!` (current) |

So the earliest checkable releases crash outright, a middle band names the
internal error explicitly, and the current wording drops the "Internal
Compiler error" prefix but is otherwise the same `llvm::cast` message —
still not the "using uninitialized value to access structured buffer"
diagnostic requested here. A control shader with the index initialized
(`uint X = 0;`) compiles cleanly and emits ordinary DXIL, confirming the
failure is specific to the uninitialized read, not the structured-buffer
array-member access in general.

The single existing comment links #5040 for reference; that report is a
different construct (`ByteAddressBuffer.Load` with an uninitialized index)
and a different symptom (silent success with no diagnostic at all, versus
the bad diagnostic reported here), so it's noted but not treated as the
same defect.

Suggest adding **`diagnostic`** — the ask here is specifically about the
quality of the diagnostic text, which is what that label is for. `bug`,
`crash` and `incorrect-code` all still apply as-is.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5040](https://github.com/microsoft/DirectXShaderCompiler/issues/5040) Undefined value allowed for buffer load index

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5040](https://github.com/microsoft/DirectXShaderCompiler/issues/5040).

Still reproduces on `main` (Debug build at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):

```
$ dxc -T ps_6_0 -E main repro.hlsl
$ dxc -dumpbin out.dxil
  %2 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 undef, i32 undef)
```

Exit 0, no warning or error printed, and the default (non-`-Vd`) DXIL validator raises no
complaint either — the load index is emitted as `undef` exactly as originally reported.
Confirmed across every stable release from `v1.4.1907` (2019) through `v1.9.2607` (current
newest) plus [Compiler Explorer](https://godbolt.org/z/cP8cW1v3x) (older DXC + `dxc_trunk`; see
the banner comment for what to look for): this has never once been diagnosed in DXC's shipped
history.

`-Wuninitialized` still catches it today (as @llvm-beanz noted in 2023), and it is still not on
by default.

@damyanp's 2024-08-27 comment re-scoped this onto the validator ("the validator should have
caught it") — that gap is exactly what's confirmed still open here: the bundled validator
accepts an `undef` resource-load index silently on every measured build. Given that this is a
documented FXC/DXC divergence (FXC's `error X4575`, quoted in the original report, was not
independently re-verified here but is not in dispute), consider adding `fxc-disagrees` in
addition to the existing `bug`, `dxil`, `incorrect-code`, `validation` labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5059](https://github.com/microsoft/DirectXShaderCompiler/issues/5059) HLSL loop optimization results in an unsupported i33 type

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5059](https://github.com/microsoft/DirectXShaderCompiler/issues/5059).

Still not fixed, but the failure mode has changed. Tested on `main`
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, local version `1.9.0.5465`)
with `dxc -T cs_6_3 -ECSMain repro.hlsl` (the maintainer-corrected repro
command; see below on the literal filed command).

**Root cause unchanged.** The loop

```hlsl
while (processed != input) { result += processed; processed++; }
```

still gets rewritten by SCEV into the closed-form
`((input-1)*(input-2))/2`, widened by one bit to `i33` to guard the
intermediate multiply against overflow. Confirmed on `main` with `-Vd`
(validation skipped) that the same illegal sequence is still produced
internally:

```
%7  = zext i32 %6 to i33
%10 = mul i33 %7, %9
%11 = lshr i33 %10, 1
%12 = trunc i33 %11 to i32
```

**What changed:** through `v1.9.2602.24` (2026-05-27) this reached the
disassembly and dxc exited 0 -- a silent correctness bug (exactly the
symptom in this issue). Starting at `v1.9.2607` (2026-07-29), and still
true on `main`, the DXIL validator's `Types.IntWidth` rule now catches it:

```
error: Int type 'i33' has an invalid width.
Validation failed.
```

exit `0x80004005`. Full linear scan shows the silent shape on 19 stable
releases (`v1.4.1907` → `v1.9.2602.24`); only `v1.9.2607` and `main`
show the caught shape -- a single, clean transition. Likely (not certain) source:
[#8207](https://github.com/microsoft/DirectXShaderCompiler/pull/8207)
("Make validator reject unsupported llvm integer sizes", fixing #6563)
extended the width check to ordinary instruction operands, not just
struct members -- but its merge date (2026-03-10) precedes
`v1.9.2602.24`'s build by two months and that release still shows the
old behavior, so attribution to a precise commit isn't proven, only the
release-level bracket is.

Compiler Explorer, `dxc_1_6_2112` (silent) vs `dxc_trunk` (caught) side
by side: https://godbolt.org/z/PGGE6r8s9

Separately, the exact command as filed (`-T lib_6_3 i33.hlsl -Fc
i33.dxil.txt`, no `-E`) no longer reaches this at all on current `main`:
without `[shader("compute")]`, `CSMain` isn't recognized as a library
entry point, so it compiles an *empty* library with only "attribute
ignored" warnings. That command did reach the bug back at `v1.4.1907`
(2019-07), so something about library-mode entry-point recognition
tightened separately at some later, undated point -- a different
question from this one. The maintainer's own corrected repro
(`-T cs_6_3 -ECSMain`, from the second, working godbolt link) is what
still demonstrates the underlying defect today.

Labels look right as-is (`bug, dxil, correctness, validation`); no
changes proposed against the current label taxonomy.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5064](https://github.com/microsoft/DirectXShaderCompiler/issues/5064) Improve DXIL Validator Testing Infrastructure

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5064](https://github.com/microsoft/DirectXShaderCompiler/issues/5064).

Partially addressed as of `main` (`89e2f98e2`) — one of the two asks in this thread is resolved,
the other is not.

**Still open:** a LIT-compatible workflow for testing the DXIL validator itself. The
`%dxilver`/`%dxv` FileCheck-style tests this issue is about
(`tools/clang/test/HLSLFileCheck/validation/`, ~150 files) remain excluded from `lit` discovery —
`tools/clang/test/HLSLFileCheck/lit.local.cfg` still sets `config.suffixes = []`, set by #5537
(2023-08-18) as part of a blanket cleanup of ~10K unsupported-test discoveries, replacing an even
blunter `config.unsupported = True` from #4822 (2022-11-29). I confirmed this directly with
`lit --show-tests` against the built tree: both `HLSLFileCheck` and `DXILValidation` report
"contained no tests". The only way these tests run today is a manual, one-directory-at-a-time
TAEF invocation (`hcttest.cmd -filecheck <path>` → `CompilerTest::ManualFileCheckTest`), not
`check-all`/CI. Tests are still being added to this unreachable tree as recently as #6172
(2024-01-22), so this isn't just stale history. A separate, newer directory,
`tools/clang/test/HLSLFileCheckLit/`, shows a partial LIT migration has begun for HLSL codegen
tests generally — but it has no `validation` subdirectory, so validator tests specifically
haven't been part of that effort.

**Resolved:** the follow-up comment's narrower ask, "missing test coverage for external
validator workflows." `tools/clang/test/DXC/validate_1_6_2112.test`, `validate_1_7_2308.test`,
`validate_1_8_2502.test`, and `version_interface.test` now cover loading an external/older
validator via `DxcDllExtValidationLoader`, and are genuinely `lit`-discovered (confirmed via
`--show-tests`). Added by #7749 (2025-10-27), fixed up by #8075 (2026-01-22).

No shader or single `dxc` invocation applies here (this is a test-infrastructure design
question), so no CE link or release-history bisect is included; the timeline has no PRs
cross-referencing this issue, so this determination rests entirely on the current state of the
test tree rather than a linked resolution.

Given the core LIT-migration ask is still unaddressed, suggest keeping `tech-debt` and adding
`test` (existing label: "Test issues or more test coverage needed") to make this discoverable
alongside other test-infrastructure work.

---
<sub>Triaged with AI assistance from direct `lit --show-tests` discovery runs and `git log`/`git
show` evidence in this repository, not a compiler run against a shader; please flag anything that
looks wrong.</sub>
````

### Draft — [#5072](https://github.com/microsoft/DirectXShaderCompiler/issues/5072) Header output option `-Fh` results in invalid default identifier for library targets

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5072](https://github.com/microsoft/DirectXShaderCompiler/issues/5072).

**Still reproduces on `main`** (`89e2f98e2`; the local build reports
`1.9.0.5465`), on **all 21 releases I could measure** (v1.4.1907, 2019-07-15,
through v1.9.2607, 2026-07-29), with `-T lib_6_3 -Fh <file>` and no `-Vn`:

```
const unsigned char g_lib.no::entry[] = {
```

exactly the invalid identifier quoted in the report. Feeding that header to
MSVC directly confirms it does not compile, as either C or C++:

```
out-header.h(78): error C2143: syntax error: missing '{' before '.'
out-header.h(78): error C2059: syntax error: '.'
```
```
out-header.h(78): error C2653: 'no': is not a class or namespace name
out-header.h(78): error C2146: syntax error: missing ';' before identifier 'entry'
```

The `-Vn <name>` workaround remains a full fix: the same header, generated
with an explicit name, compiles clean as both C and C++ with no other change.

**#8074**, closed 2026-01-20 as a duplicate of this one, is worth noting here:
it reproduced the identical `g_lib.no::entry` string against `lib_6_5`, and
@damyanp's comment there repeats "we don't plan on scheduling time to work on
this" — so as of ten months ago the team still had this in the same
not-proactively-fixed state described in 2024.

### Cause

`HLSLOptions.cpp` assigns `opts.EntryPoint = "lib.no::entry"` unconditionally
for every library profile — a sentinel meant to be unreachable — and
`dxc.cpp`'s `-Fh` default-name logic (`"g_" + EntryPoint`) has no library-
profile special case, so the sentinel flows straight into the generated
identifier. A non-library `-Fh` case (e.g. `cs_6_0`) is unaffected on every
release measured; the defect is specific to library profiles, not `-Fh` in
general. `git log -S` on the sentinel string finds only its introduction,
`8e21407ca` (2017-05-12, "Add library profile."), never touched since — this
was never a regression to bisect.

No Compiler Explorer link: the bug is entirely inside the `-Fh` file that
CE's API has no channel to return (see `verdict.json`'s `godbolt_skip` for
detail).

Given the workaround has existed the whole time and the maintainer response
already covers the product decision, I'd leave `bug` and `low-hanging-fruit`
as-is and suggest adding `shader-linking` (library-target-specific bug); no
removals.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5079](https://github.com/microsoft/DirectXShaderCompiler/issues/5079) Conflict with DirectX-Headers

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5079](https://github.com/microsoft/DirectXShaderCompiler/issues/5079).

Still reproduces on `main` (main-debug @ `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).

This is a genuine header conflict, not something specific to your build: DXC's own
non-Windows shim (`include/dxc/WinAdapter.h`, pulled in by `dxc/dxcapi.h` whenever
`_WIN32` is undefined) and DirectX-Headers' own non-Windows shim
(`wsl/winadapter.h`/`wsl/stubs/basetsd.h`) each independently define the same set of
Windows base types, with different underlying types for several of them. Reproduced
locally with this repository's own vendored copies of both header trees — DXC's
`include/dxc/WinAdapter.h` and the pinned DirectX-Headers submodule's
`wsl/winadapter.h` (the pre-split, single-file predecessor of the `wsl/stubs/*.h`
form your build hits; same content, per the investigation in #8431 below) —
compiled with `clang -U_WIN32` (no dxc.exe angle applies; this is a C++ preprocessor
question, not a shader-compilation one):

```
include/dxc/WinAdapter.h:303:14: error: typedef redefinition with different types ('BYTE' (aka 'unsigned char') vs 'char')
include/dxc/WinAdapter.h:306:14: error: typedef redefinition with different types ('bool' vs 'uint32_t' (aka 'unsigned int'))
include/dxc/WinAdapter.h:310:14: error: typedef redefinition with different types ('long' vs 'int32_t' (aka 'int'))
include/dxc/WinAdapter.h:312:23: error: typedef redefinition with different types ('unsigned long' vs 'uint32_t' (aka 'unsigned int'))
include/dxc/WinAdapter.h:376:16: error: redefinition of '_GUID'
```

(paths shown relative to the repo; full capture in `manual-case-clang-conflict.txt`).

**Nothing has changed since this was filed.** The DirectX-Headers submodule pin
(`980971e835876dc0cde415e8f9bc646e64667bf7`) has not moved since it was first added to
this repository in 2022-11-23 (PR #4810) — before this issue was even filed.

A fix already exists: PR #8431 ("Update DirectX-Headers to latest", opened
2026-05-08) bumps the submodule and removes the now-duplicated types from
`WinAdapter.h`. It's open and mergeable, but discussion has stalled since
2026-05-11 on two unresolved design questions its own author raised: `BOOL`'s
underlying type changing from `bool` to `uint32_t` (an ABI-visible change for a
public type), and whether users of the released `dxc/dxcapi.h`/`WinAdapter.h` as a
standalone installed header would now need DirectX-Headers on their own include
path too. Both need a maintainer decision, not another investigation — the repro
and root cause are already well understood.

Suggest keeping the `build` label and adding `linux`: the conflict is entirely in
the non-Windows (`_WIN32`-undefined) code path of both shims.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5080](https://github.com/microsoft/DirectXShaderCompiler/issues/5080) cbuffer assert when using -fspv-debug=vulkan-with-source

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5080](https://github.com/microsoft/DirectXShaderCompiler/issues/5080).

This complete repro is fixed on current main
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`). The as-filed command exits 0 and
emits SPIR-V, including a `DebugTypeComposite`/`DebugGlobalVariable` pair for the
cbuffer. Dropping `-fvk-use-dx-layout` (as @s-perron suggested) also exits 0, matching
the workaround given in-thread.

The stable-release boundary is v1.8.2403.2 → v1.8.2405:

```text
v1.8.2403.2: exit 0xC0000005
Internal compiler error: access violation. Attempted to read from address ...

v1.8.2405: exit 0
; SPIR-V
```

The bug actually goes back further than that boundary alone suggests: v1.6.2112,
the oldest release able to parse `-fspv-debug=vulkan-with-source` at all, also
crashes once probed with a target-env value it accepts (its native rejection of
`vulkan1.3` had made it look clean). [Compiler Explorer](https://godbolt.org/z/9rshx68rz)
shows the same thing — DXC 1.6.2112 (`-fspv-target-env=vulkan1.0` substituted for the
unsupported `vulkan1.3`) terminates with `SIGSEGV`, and trunk compiles successfully.

The likely fix is commit
[`1e59ce9185`](https://github.com/microsoft/DirectXShaderCompiler/commit/1e59ce9185485535011e1f706d1ab3c1b349eac1)
(#6531), which removes exactly the assert this issue quotes and discusses DX-layout-driven
cbuffer lowering. This is not build-verified against its parent (a local toolchain
incompatibility blocked building that old a commit), so call it strong, not certain,
attribution rather than a settled one.

I suggest adding `crash`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5105](https://github.com/microsoft/DirectXShaderCompiler/issues/5105) Allow unused registers to be output to reflection

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5105](https://github.com/microsoft/DirectXShaderCompiler/issues/5105).

Still an open gap on `main` (built locally at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`dxc --version`: `1.9.0.5465 (triage, 7665270b9)`). With an explicitly-registered but unreferenced
resource (`Texture2D unusedTex : register(t1);`, never read by the entry point), the disassembly's
`Resource Bindings` table only lists the resources that are actually used:

```
; Name                                 Type  Format         Dim      ID      HLSL Bind  Count
; ------------------------------ ---------- ------- ----------- ------- -------------- ------
; samp                              sampler      NA          NA      S0             s0     1
; usedTex                           texture     f32          2d      T0             t0     1
```

`-O0`, tried as suggested in the report, does not change this. This has been the case in every
stable release checked back to v1.4.1907 (2019) — it isn't a regression, the option has simply
never existed.

There's now active, in-progress work in this exact area, surfaced by this issue's own
cross-reference timeline:

- [#7643](https://github.com/microsoft/DirectXShaderCompiler/pull/7643) — open, unmerged —
  `-fhlsl-unused-resource-bindings=reserve-all`, for consistent binding assignment.
- [#7734](https://github.com/microsoft/DirectXShaderCompiler/pull/7734) — open, unmerged,
  explicitly titled step 2/2 for this issue — `-keep-all-resources`, to keep unused resources
  visible in reflection without emitting `createHandle` for them.

Neither flag is recognised by the current build (`Unknown argument: '-keep-all-resources'` /
`Unknown argument: '-fhlsl-unused-resource-bindings=reserve-all'`), so the request is not yet
satisfied, but it does look like it's being actively worked rather than sitting idle. Compiler
Explorer corroborates the current-`main` state on the DXC trunk build:
https://godbolt.org/z/snfK4ebdG

Suggest keeping this open (`still-valid-keep-open`) and adding the `reflection` label, since the
whole ask is about reflection data stability.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5115](https://github.com/microsoft/DirectXShaderCompiler/issues/5115) signed/unsigned overload resolution error seems unjustified

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5115](https://github.com/microsoft/DirectXShaderCompiler/issues/5115).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), with the exact
diagnostic quoted above. It reproduces the same way on every stable release checked,
`v1.4.1907` (2019-07) through `v1.9.2607` (2026-07) — this has never worked as gcc's C++ rules
would suggest, on any release we can measure.

Compiler Explorer: https://godbolt.org/z/xPz8ndv7T

- `dxc_1_6_2112` and current `dxc_trunk` both still report `f(1)` as ambiguous.
- The new Clang-based HLSL front end (`hlsl_clang_trunk`) compiles the identical source with
  **no diagnostic at all**. That matches what @llvm-beanz described above: the HLSL 202x
  overload-rules rewrite adopts C++ overload rules, and it looks like this specific case is
  already fixed there. (Checked that this isn't just Clang being permissive: a
  genuinely-ambiguous variant, `f(1.0f)` against the same two overloads, is correctly rejected
  by both `dxc_trunk` and `hlsl_clang_trunk`, with identical wording.)

So current (classic) `dxc` still has the reported behavior, and it's not new — nothing to
close here — but the successor front end already resolves it the way this issue asks for.

Suggested labels: keep `bug` and `hlsl-next`; consider adding `diagnostic` (the symptom is
specifically a wrong/unjustified diagnostic on valid input) and `type-system` (the underlying
defect is in how integer-literal arguments are ranked against `int`/`unsigned int` overloads).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5116](https://github.com/microsoft/DirectXShaderCompiler/issues/5116) Weird behavior when returning texture

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5116](https://github.com/microsoft/DirectXShaderCompiler/issues/5116).

Still reproduces on `main` (built from commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).

Compiling the repro at `-T cs_6_6` succeeds silently, exit 0, while the identical source at
`-T cs_6_5` is correctly rejected:

```
repro.hlsl:68:18: error: local resource not guaranteed to map to unique global resource.
        else t = tex2d.SampleGrad(anisoSampler, uv, uvDdx, uvDdy);
```

That asymmetry is present at v1.6.2104 (2021-04-20, the oldest release shipping SM 6.6) and at
v1.9.2607 (today's newest) — both endpoints of the shipped-SM-6.6 range agree, so the tool's
binary search did not need to probe intervening releases individually — and on today's
`dxc_trunk` on Compiler Explorer: <https://godbolt.org/z/eE8co66vG> (pane 1/2: `-T cs_6_6` on
CE's oldest DXC and on trunk, both clean; pane 3: `-T cs_6_5` on trunk, same diagnostic).
Releases older than v1.6.2104 don't apply — SM 6.6 didn't exist yet.

The two separately-actionable items from @llvm-beanz's comment above are both still open:
(1) per that comment's hypothesis, SM 6.6 should also reject this, because
`DXILCondenseResources` doesn't see through the SM 6.6 resource-handle annotations the way it
does for earlier profiles; (2) full control-flow flattening that would eliminate the underlying
`phi`/`undef` (and make the shader legal either way) is a separate change that this triage does
not newly assess.

Current labels (`dxil`, `correctness`, `incorrect-code`) already match this finding.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5117](https://github.com/microsoft/DirectXShaderCompiler/issues/5117) Dumping header dependencies to file prevents error output

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5117](https://github.com/microsoft/DirectXShaderCompiler/issues/5117).

This still reproduces on `main` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), and it is a bit
worse than described: with `-MD`/`-MF` (or plain `-M`), `dxc` doesn't just fail to print
diagnostics — it reports a **successful compile (exit 0)** for source it would otherwise
correctly reject.

```
$ dxc -T ps_6_0 -E main repro.hlsl
repro.hlsl:3:10: error: use of undeclared identifier 'badIdentifierNotDeclared'
  return badIdentifierNotDeclared;
         ^

$ dxc -T ps_6_0 -E main -MD -MF repro.d repro.hlsl
(exit 0, no output at all)
```

Compiler Explorer, same source, same two invocations: https://godbolt.org/z/s4Mcsxj66

The cause: `-M`/`-MD`/`-MF` all set a single `opts.DumpDependencies` flag
(`lib/DxcSupport/HLSLOptions.cpp`), which routes `DxcContext::Compile` through
`clang::PreprocessOnlyAction` (`tools/clang/tools/dxcompiler/dxcompilerobj.cpp`, the
`DumpDependencies` branch) instead of the normal compile action. That action never constructs a
`Parser` or `Sema`, so no parse- or semantic-level diagnostic is ever produced — there's nothing
for the later `hasErrorOccurred()` check to see. Preprocessor-level errors (e.g. a missing
`#include`) still surface correctly, since the preprocessor *is* what runs in this mode; it's
specifically parser/Sema diagnostics (undeclared identifiers, missing semicolons, etc.) that go
missing. This has been true since dependency dumping was added
(#4017, Dec 2021) — every release that has the flag at all reproduces this.

Given a build could treat this exit code as "the shader is fine," I'd suggest `bug` and
`diagnostic` in addition to the existing `high-impact`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5165](https://github.com/microsoft/DirectXShaderCompiler/issues/5165) Validation error on switches having 8 cases: "I8 can only used as immediate value for intrinsic"

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5165](https://github.com/microsoft/DirectXShaderCompiler/issues/5165).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), and always has:
a linear scan of every stable release from v1.4.1907 through v1.9.2607 reproduces it, so this
has never worked, not regressed.

@damyanp is right that this isn't a validation bug: the validator is correctly rejecting IR
that should never have been generated. The root cause is in `SimplifyCFG`'s
`SwitchToLookupTable` transform. When a switch's optimizer-generated lookup table has "holes"
and the `default:` case can't be folded to a compile-time constant, the transform builds a
"hole check" bitmask whose width is `NextPowerOf2(max(7, TableSize - 1))`. For a table size of
8 or less that's exactly 8, producing an illegal `i8` truncation:

```
error: I8 can only be used as immediate value for intrinsic or as i8* via bitcast by lifetime
intrinsics.
note: at '%10 = trunc i32 %3 to i8' in block '#2' of function 'ShaderDomain_Cs'.
```

This is the sibling of a bug already fixed for the switch's separate *result* bitmap (rounded
up to >= 16 bits in a prior fix for a different, unrelated issue) — but that fix never touched
this "hole check" mask width computation, which still uses the old formula.

Minimal repro (reconstructed; the original Shader Playground link is dead):

```hlsl
RWStructuredBuffer<uint> buf : register(u0);

[numthreads(1,1,1)]
void ShaderDomain_Cs(uint3 id : SV_DispatchThreadID)
{
    uint x = buf[0];
    bool result;
    switch (x)
    {
    case 0: result = true; break;
    case 1: result = true; break;
    case 2: result = true; break;
    case 3: result = true; break;
    case 4: result = true; break;
    case 5: result = true; break;
    case 7: result = true; break;
    default: result = (buf[1] != 0);
    }
    buf[0] = result ? 1 : 0;
}
```

Compiler Explorer (dxc 1.6.2112 and trunk both fail the same way):
https://godbolt.org/z/qPfqjxxnY

Suggested label: `correctness`, in addition to `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5169](https://github.com/microsoft/DirectXShaderCompiler/issues/5169) Add D3D\_SVC\_BIT\_FIELD to D3D\_SHADER\_VARIABLE\_CLASS

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5169](https://github.com/microsoft/DirectXShaderCompiler/issues/5169).

Still open and still accurate, checked against `main` at
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.

The vendored `external/DirectX-Headers` submodule (pinned at
`980971e83587...`) still declares `D3D_SHADER_VARIABLE_CLASS` with members
`D3D_SVC_SCALAR` through `D3D_SVC_INTERFACE_POINTER` only — no
`D3D_SVC_BIT_FIELD`. DXC's own source still works around exactly that, in
both `lib/HLSL/DxilContainerReflection.cpp` and
`lib/DxilContainer/D3DReflectionStrings.cpp`:

```c
// FIXME: remove the define once D3D_SVC_BIT_FIELD added into
// D3D_SHADER_VARIABLE_CLASS.
#define D3D_SVC_BIT_FIELD                                                      \
  ((D3D_SHADER_VARIABLE_CLASS)(D3D_SVC_INTERFACE_POINTER + 1))
```

`git log --all -S "D3D_SVC_BIT_FIELD"` lists three commits touching these
files; only #5142 (which added the workaround) writes new text, and the
other two are file moves that carry it forward unchanged. The gap this issue
tracks has been open since #5142 merged on 2023-05-05.

This isn't something a shader compile can show either way — DXC already
supplies the value itself regardless of the header, so behavior is identical
before and after the header is fixed. The remaining work is exactly what the
issue says: add `D3D_SVC_BIT_FIELD` to the real `D3D_SHADER_VARIABLE_CLASS`
enum, then drop the `#define ADD_SVC_BIT_FIELD` workaround (and its FIXME) in
both files above.

Current labels (`bug`, `hlsl2021`, `reflection`) still fit; no changes
suggested.

---
<sub>Triaged with AI assistance. Findings were verified by reading the cited
source files directly; please flag anything that looks wrong.</sub>
````

### Draft — [#5172](https://github.com/microsoft/DirectXShaderCompiler/issues/5172) IDxcIndex::ParseTranslationUnit has no mechanism to honor an IDxcIncludeHandler

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5172](https://github.com/microsoft/DirectXShaderCompiler/issues/5172).

Still an open gap on current `main` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`1.9.0.5465`). `IDxcIndex::ParseTranslationUnit`'s parameter list
(`include/dxc/dxcisense.h:802-808`) still has no per-request include callback like
`IDxcIncludeHandler` — the only related parameter is `IDxcUnsavedFile **unsaved_files`, and the
implementation (`tools/clang/tools/libclang/dxcisenseimpl.cpp`) still binds unconditionally to a
disk filesystem otherwise.

A small harness confirms the gap on this build, same DLL, same repro:

```
[pti-absent]   file removed, no unsaved-file override  -> "'myinclude.hlsli' file not found"
[pti-unsaved]  file removed, pre-declared via IDxcUnsavedFile -> resolves (0 diagnostics)
[compile-handler] IDxcCompiler::Compile, file removed, served only by a custom
                  IDxcIncludeHandler -> handler invoked once, content served with zero
                  disk backing
```

`IDxcUnsavedFile` is the only substitute `ParseTranslationUnit` has, and it is static: content
must be pre-declared under its exact path before the call, not served per-request the way
`Compile`'s `IDxcIncludeHandler::LoadSource` is. The last case shows that same dynamic callback
genuinely working on this build's `Compile` — confirming the gap is specific to
`ParseTranslationUnit`, not a general limitation.

This behaviour predates the issue: the disk-only implementation and its "TODO: until an
interface to file access is defined" comment trace back to the project's original 2016 commit,
confirmed as an ancestor of `v1.4.1907` (2019-08-30) — unchanged since.

@llvm-beanz's 2023-07-13 comment still reads as the project's position: unlikely to be
prioritized, patches welcome, and the longer-term direction is to retire the IntelliSense
interface in favor of upstream LSP-based tooling rather than extend it with this mechanism.
Nothing here contradicts that.

Suggest adding `api` (currently only `enhancement`).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5173](https://github.com/microsoft/DirectXShaderCompiler/issues/5173) IDxcCursor misses semantics

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5173](https://github.com/microsoft/DirectXShaderCompiler/issues/5173).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
built Debug).

Confirmed with a small standalone harness that loads `dxcompiler.dll` and
drives `IDxcIntelliSense`/`IDxcTranslationUnit`/`IDxcCursor` directly on a
shader with a semantic on a struct field, a function parameter, and the
return type (`SV_POSITION`, `TEXCOORD0`, `NORMAL0`, `SV_TARGET`). The parsed
cursor tree contains **no attribute-kind cursor at all** for any of the
three — not even the generic `DxcCursor_UnexposedAttr` an ordinary
unrecognised Clang attribute would produce. A control shader with a real
`[numthreads(...)]` attribute alongside a semantic on the same function
confirms the harness does surface an attribute cursor (`UnexposedAttr`) when
one genuinely exists; only the semantic side is silent. Same result on the
oldest and newest catalogued release builds (v1.4.1907, v1.9.2607) as on
`main`, and `git log` shows no commit has ever touched libclang's
`CXCursorKind` mapping for an HLSL attribute — this has been the case for as
long as the behavior is checkable.

Source explains why: `HLSLSemantic` is declared in `Attr.td`, but nothing in
the compiler ever constructs an `HLSLSemanticAttr` — semantics are recorded
through a separate mechanism, `hlsl::UnusualAnnotation`/`SemanticDecl`
(`Decl::getUnusualAnnotations()`), which is never visited by libclang's
`CursorVisitor::VisitAttributes` (it only walks `Decl::attrs()`). So this
isn't an attribute that libclang exposes generically and DXC never
special-cased — it's a side-channel `IDxcCursor` structurally cannot reach
at all.

Given the existing reply that this area is deprioritized in favor of LSP
tooling, suggesting `enhancement-not-bug` rather than a bug label — the
compiler isn't misbehaving; the interface was never extended for this.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5175](https://github.com/microsoft/DirectXShaderCompiler/issues/5175) IDxcCursor does not support template parameter and template argument querying

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5175](https://github.com/microsoft/DirectXShaderCompiler/issues/5175).

Confirmed still missing on current `main` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):
`IDxcCursor` (`include/dxc/dxcisense.h`) has template cursor kinds but no
`GetNumTemplateArguments`/`GetTemplateArgumentKind`/`GetTemplateArgumentValue`-style methods.
The only argument accessors, `GetNumArguments`/`GetArgumentAt`, forward to libclang's generic
`clang_Cursor_getNumArguments`/`clang_Cursor_getArgument`; no template-specific equivalents are
wired.

The underlying `clang_Cursor_getNumTemplateArguments` family already exists in this repo's
libclang fork (`tools/clang/tools/libclang/CXCursor.cpp`, exported in `libclang.exports`) but is
still pre-D134416, gated on `clang_getCursorKind(C) == CXCursor_FunctionDecl` via
`FunctionDecl::getTemplateSpecializationInfo()`. Only 4 commits have touched that file, and none
add template-argument handling. Without porting D134416's class-template/partial-specialization
extension into `CXCursor.cpp`, wiring `IDxcCursor` alone would still return `-1`/`Invalid` for a
class-template cursor such as `Foo<float, -2, 3>`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5184](https://github.com/microsoft/DirectXShaderCompiler/issues/5184) WaveMatch with a vector input value

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5184](https://github.com/microsoft/DirectXShaderCompiler/issues/5184).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), with the same
validator diagnostic:

```
error: validation errors
repro.hlsl:3:12: error: Instructions must be of an allowed type.
note: at '%10 = insertvalue %dx.types.fouri32 %5, i32 %9, 0' in block '#0' of function 'main'.
Validation failed.
```

A few corrections/additions to the report:

- **The trigger is `-Od` alone, not "debug mode."** `-Zi` is incidental — `-Od` with or
  without `-Zi` fails; an optimized build with `-Zi` still compiles clean. The optimizer
  isn't required, just disabled.
- **Not `uint4`-specific.** @pow2clk's linked repro uses `float4` and hits the identical
  diagnostic, because `WaveMatch` always *returns* `uint4` regardless of the argument's
  element type — a scalar (non-vector) argument compiles fine under the same flags.
- **The mechanism isn't "not scalarized."** Both the optimized and `-Od` builds already lower
  the call into four separate per-lane `waveMatch.i32` calls. What differs is how the four
  per-lane masks are recombined: the optimized build `extractvalue`s and `and`s them directly,
  while `-Od` codegen rebuilds a single aggregate via repeated `insertvalue` on the
  `%dx.types.fouri32` result type — which the validator's aggregate-type rule forbids. So this
  is the generic unoptimized-codegen path for aggregate-typed intrinsic results, not a missing
  scalarization pass specific to `WaveMatch`.
- **Always reproduced, never worked.** Across every stable release that can express the
  target profile (v1.6.2104 through the current v1.9.2607, 18 releases), none compile it
  clean; the two oldest catalogued releases predate the SM6.6 profile itself and can't run
  the repro at all. This is not a regression.
- **On the Clang expectation:** `hlsl_clang_trunk` doesn't confirm or refute it — Clang hasn't
  implemented `WaveMatch` yet (`use of undeclared identifier`), and separately rejects
  `uint4`-typed `SV_Target` outright, so today's front end can't even parse this repro's
  signature. It's a plan for the new front end, not a measured result yet.

Compiler Explorer, `dxc_1_6_2112` and `dxc_trunk` (both reproduce identically):
https://godbolt.org/z/GjKe8bn5b

Suggest adding `validation` (the failure is specifically a DXIL validation rejection) and
`up-for-grabs`, matching the intent already stated above.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5194](https://github.com/microsoft/DirectXShaderCompiler/issues/5194) Impossible to add template on operator() overload

````markdown
> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5194](https://github.com/microsoft/DirectXShaderCompiler/issues/5194).

Still reproduces on `main` (Debug build, commit `89e2f98e2`). All three call
forms still error:

```
repro.hlsl:11:5: error: no matching function for call to object of type 'Test'
    t(5);
    ^
repro.hlsl:12:7: error: unexpected type name 'uint': expected expression
    t<uint>(5);
      ^
repro.hlsl:13:7: error: no matching member function for call to 'operator()'
    t.operator()<uint>(5);
    ~~^~~~~~~~~~~~~~~~
```

Compiler Explorer, current `dxc_trunk` alongside CE's oldest DXC
(`dxc_1_6_2112`): https://godbolt.org/z/9ajqv56xK -- identical result on
both.

History: `-HV 2021` didn't exist before v1.6.2112 (2021-12), so older releases
are invalid probes (they reject the flag before parsing anything); `bisect`
reports always-repro'd from v1.6.2112 (17 months before this report) through
the latest release, v1.9.2607. This was never implemented, not a regression.

On the successor Clang-based HLSL front end: testing each call form in
isolation, `hlsl_clang_trunk` already accepts `t(5)` and
`t.operator()<uint>(5)` -- the two forms that are valid C++ -- and only
still rejects `t<uint>(5)`, which isn't valid C++ syntax either. So the
new front end's behavior on this input already matches C++ overload rules.

Suggested labels: no change -- `bug` and `hlsl-next` already describe this
correctly.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5244](https://github.com/microsoft/DirectXShaderCompiler/issues/5244) [SPIR-V][SM6.7] Add support for RWTexture2DMS in the SPIR-V backend

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5244](https://github.com/microsoft/DirectXShaderCompiler/issues/5244).

**Still reproduces** on `main` (upstream `89e2f98e29c2`, Debug build; the local binary
self-reports a fork-local merge commit whose source tree is identical to that public commit
outside triage tooling). With the repro exactly as filed:

```
$ dxc -spirv -Zi -fspv-reflect -E PS -T ps_6_7 repro.hlsl
Internal compiler error: LLVM Assert            # exit 0xE0000001
```

The same shader compiles cleanly to DXIL, matching what the original report showed.

Two things worth adding to the original report:

**It's a crash, not only an unimplemented case.** Under a debugger, this trips two chained
asserts in `clang::spirv::PreciseVisitor::isAccessingPrecise`
(`tools/clang/lib/SPIRV/PreciseVisitor.cpp:72`, then `include/llvm/ADT/ArrayRef.h:197`) — an
out-of-range access into the multisample resource's SPIR-V struct fields. Continuing past both
(emulating a Release/`NDEBUG` build) shows the *codegen itself* is broken, not just the assert:
DXC's own embedded SPIR-V validator then rejects the module it just built:

```
fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-UniformConstant-04655]
UniformConstant OpVariable <id> '7[%gUav]' has illegal type.
```

**Every shipped release fails the same way, just without the debugger.** All 19 probeable
stable releases from v1.5.2010 (2020-10, before this issue was filed) through v1.9.2607 hit
the same invalid-SPIR-V path; with the assert compiled out under `NDEBUG` they get far enough
for the validator to reject it cleanly instead (exit `E_FAIL`, older releases print a
plainer `error: unknown shader module: invalid`). v1.4.1907 was not built with SPIR-V
support at all and can't probe this. So this has never worked in SPIR-V, on any checkable
release — not a regression, and not close to fixed on `main` either.

[Compiler Explorer](https://godbolt.org/z/oj91s731v): `dxc_1_6_2112` and `dxc_trunk` both
still fail the same way.

Suggested labels: add **`bug`** and **`crash`** alongside the existing `enhancement` — this
is more than a missing feature, it's a reachable assert from valid HLSL.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5255](https://github.com/microsoft/DirectXShaderCompiler/issues/5255) Rewriter removed struct declaration which used in constant buffer.

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5255](https://github.com/microsoft/DirectXShaderCompiler/issues/5255).

Still reproduces on current `main` (89e2f98e2, 2026-08-19). Running `dxr -remove-unused-functions -remove-unused-globals -E vs_main` on the shader in the issue produces output byte-identical to what's quoted above: both `cbuffer` blocks are kept (unused cbuffers are intentionally kept by this rewriter), but the `struct InstanceDataStructType { ... };` declaration they both reference is deleted — the emitted HLSL references an undeclared type and will not recompile.

Root cause: `InstanceDataStructType` is only referenced as the **element type of an array-typed** cbuffer member (`InstanceDataStructType mData[2];`). `VisitHLSLBufferDecl` in `tools/clang/tools/libclang/dxcrewriteunused.cpp` marks a cbuffer member's type as "used" via `memberDecl->getType()->getAsTagDecl()`, and `getAsTagDecl()` does not unwrap array types — so it returns null for an array member and the struct is never marked used. A same-shaped control with a **scalar** member (`InstanceDataStructType mData;`, no array) correctly keeps the struct declaration; only the array form loses it. This has reproduced on every stable release able to express these rewriter options, `v1.5.2010` (2020-10-22) through `v1.9.2607`, and on `main`; `v1.4.1907` predates the rewriter's `-remove-unused-*` option support entirely.

This was already root-caused and fixed once: [#5265](https://github.com/microsoft/DirectXShaderCompiler/pull/5265), opened two days after this issue, adds a `MarkUsedType` helper that also unwraps array element types, with a test using this exact repro. It built cleanly but was never merged, and was auto-closed in January for two years of inactivity, not for a technical objection.

Labels: this repo has a `rewriter` label ("Bugs in the rewriter") that isn't on this issue; suggest adding it along with `bug` and `correctness`, since the output is not just suboptimal but fails to recompile.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
````

### Draft — [#5258](https://github.com/microsoft/DirectXShaderCompiler/issues/5258) SemaHLSL's FlattenedTypeIterator does not handle bit fields properly.

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5258](https://github.com/microsoft/DirectXShaderCompiler/issues/5258).

This issue bundles three separate examples; they don't all have the same status, so I've
measured them independently against `main` (`89e2f98e2`, `1.9.0.5465`).

**Example 1** (struct-to-struct cast with equal total storage) and **Example 3** (missing
diagnostic on a cast that narrows a >32-bit bit-field struct to `uint`) **still reproduce**, with
no change across every stable release back to v1.6.2112 (the earliest release supporting
`-HV 2021`, which this issue requires):

```
repro.hlsl:22:34: error: cannot convert from 'const StructWithUint' to 'SomeStructWithBitfields'
    SomeStructWithBitfields bf = (SomeStructWithBitfields)cStructWithUint;
```

Example 3 compiles `SomeFunc2` cleanly with no error or warning on every measured build,
confirmed against a same-shape control that does warn (`implicit truncation of vector type`),
so the absence isn't an artifact of a predicate that never fires.

Example 1 is also verified on Compiler Explorer: https://godbolt.org/z/b9vP5dhMK
(`dxc_1_6_2112` and `dxc_trunk`, both reject the cast).

**Example 2** (cast from `0` failing only when the struct's *first* bit-field is enum-typed) is
**fixed**: it errored through v1.8.2502 and compiles cleanly from v1.8.2505 onward, including
`main`. The reporter's own control (a plain `uint32_t` field ahead of the enum one) compiled
cleanly at every release tested, both before and after the fix. The fix landed somewhere in a
162-commit window between v1.8.2502 and v1.8.2505 that also carries a large, unrelated
long-vector/SM6.9 refactor touching the same file; I did not isolate the exact commit, so treat
this as release-level, not commit-level. Note separately that this repro's enum value is `0`, so
it doesn't confirm a non-zero enum bit-field round-trips correctly — only that the cast is no
longer rejected.

Suggest keeping this open (Examples 1 and 3 are live bugs) and adding `type-system` and
`diagnostic` — the root cause is bit fields not being handled consistently in type conversions,
manifesting as both a wrong diagnostic (1) and a missing one (3).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5261](https://github.com/microsoft/DirectXShaderCompiler/issues/5261) DXIL: Deadlock when loading `RayDesc` from `ByteAddressBuffer`

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5261](https://github.com/microsoft/DirectXShaderCompiler/issues/5261).

This no longer reproduces on `main` (commit `89e2f98e2`, Debug build). The repro from the
issue body compiles cleanly (exit 0), and a control that actually consumes the loaded
`RayDesc` fields also compiles cleanly, with the load correctly flattened into four
`rawBufferLoad` ops in the DXIL.

Release history (`v1.4.1907` and `v1.5.2010` reject `cs_6_6` outright and can't probe this):

| | |
|---|---|
| v1.6.2104 (2021-04) .. v1.7.2207 (2022-07) | clean |
| v1.7.2212 (2022-12) .. v1.8.2502 (2025-02) | reproduces (hangs — these are Release builds, so no assert) |
| v1.8.2505 (2025-05) .. current `main` | clean |

This matches your timeline: the "previous… worked fine" compiler (`0392e60dbc8`, 2022-11-10)
lands just before the failing window, and the broken build you reported (`ea3623fdf71`,
2023-05-30) is inside it.

Likely fix candidate: 053e7ac65 ("Refactor udt intrinsic arg copy to before SROA, flatten
RayDesc", #7440), the only commit touching `ScalarReplAggregatesHLSL.cpp` between the last bad
and first clean release. This is still a lead, not a confirmed attribution.

Compiler Explorer (`dxc_1_6_2112`, `dxc_trunk`): https://godbolt.org/z/1K9zo9Mnc — both compile
without error, consistent with the above.

Suggested label: no change (`bug`, `crash` still describe the issue's history accurately).
Suggested action: close as fixed, since this is complete and clean across every release since
v1.8.2505 and on current `main`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5268](https://github.com/microsoft/DirectXShaderCompiler/issues/5268) Rewriter remove used static global variable which is used for other static global variable definition used by entryPoint

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5268](https://github.com/microsoft/DirectXShaderCompiler/issues/5268).

Still reproduces on `main` (build at `89e2f98e2`, `dxr.exe`). Running the repro exactly as
filed:

```
dxr -E VSMain -remove-unused-globals test.hlsl
```

drops the `POINT_SIZE` declaration but keeps `POINT_SIZE_3`, whose initializer still references
it. Recompiling the rewritten output fails:

```
test.hlsl:1:60: error: use of undeclared identifier 'POINT_SIZE'; did you mean 'POINT_SIZE_3'?
static const float3 POINT_SIZE_3 = float3(1.F, 1.F, 1.F) * POINT_SIZE;
                                                           ^~~~~~~~~~
```

**Root cause:** `VarReferenceVisitor::VisitDeclRefExpr` in
`tools/clang/tools/libclang/dxcrewriteunused.cpp` marks a kept global's initializer references
as used only when that initializer is exactly an `InitListExpr`, `ImplicitCastExpr`, or
`DeclRefExpr`. `POINT_SIZE_3`'s initializer, `float3(1,1,1) * POINT_SIZE`, is a binary/operator
expression — none of those three forms — so the visitor never walks into it and the reference
to `POINT_SIZE` is never discovered. This isn't specific to multiplication: any compound
initializer (vector construction, arithmetic, a function call) on a kept global can hide a
transitive reference to another global the same way.

**History:** reproduces identically on every stable release that can run this flag at all —
v1.5.2010 through the current v1.9.2607 — as well as `main`. v1.4.1907's `dxr.exe` can't be used
as a control here: `-remove-unused-globals` fails there with a generic
`Compilation failed - error code 0x80070057` on any input, including a known-good existing
rewriter test, so that release is excluded as unprobeable rather than as evidence of a fix.

No Compiler Explorer link: this is a `dxr.exe`-only rewriter defect, and `dxc.exe` itself
rejects `-remove-unused-globals` (`Unknown argument`), so no CE pane can exercise it.

Suggest keeping current labels (`bug`, `rewriter`) — no changes needed there.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5269](https://github.com/microsoft/DirectXShaderCompiler/issues/5269) Amplification shader: support for empty payload

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5269](https://github.com/microsoft/DirectXShaderCompiler/issues/5269).

Still reproduces on `main` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df), and on every stable
release since amplification shaders shipped (v1.5.2010 through v1.9.2607) — this has never
worked, it is not a regression. Compiling

```hlsl
struct Payload
{
};

[numthreads(32, 1, 1)]
void main()
{
    Payload pld;
    DispatchMesh(32, 1, 1, pld);
}
```

with `-T as_6_5 -E main` gives the same diagnostic quoted in the issue:

```
error: For amplification shader with entry 'main', payload size 4 is greater than
declared size of 0 bytes.
```

Compiler Explorer: https://godbolt.org/z/WfqfzrK91 (`dxc_1_6_2112` and `dxc_trunk`, identical
result on both).

The root cause is a one-line bug, not a broader design gap. In
`ValidateAsIntrinsics` (`lib/DxilValidation/DxilValidation.cpp`), the first payload-size
check reads the size of the **payload pointer** instead of the pointee struct:

```cpp
Value *OperandVal = DispatchMeshCall.get_payload();
Type *PayloadTy = OperandVal->getType();          // pointer type, not pointee
unsigned PayloadSize = DL.getTypeAllocSize(PayloadTy);
```

DXIL's datalayout uses 32-bit pointers, so `PayloadSize` here is always the constant 4,
regardless of the real payload size — which is why every ordinary (non-empty) payload
struct in this repo's own test suite is at least 4 bytes and never trips the bug: the
comparison `declared < 4` is false for them. An empty struct is the one case whose real
size (0, confirmed by the DXIL metadata this build itself emits) is less than that
constant, so the check fires on exactly the input this issue reports. A second,
correctly-written check 40 lines later in the same function does strip the pointer, which
is what confirms the first one doesn't.

Whether DXC should accept a zero-byte amplification-shader payload at all (matching
Vulkan's optional task-payload semantics) is a separate design question this triage
doesn't decide. But independent of that policy call, the validator's own bookkeeping is
inconsistent here: it records a declared size of 0 for this payload and then rejects it
by comparing against the wrong operand.

Suggested label: `validation` (the defect is in the DXIL validator's own payload-size
accounting, not in front-end acceptance or codegen).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5290](https://github.com/microsoft/DirectXShaderCompiler/issues/5290) Rewriter: entrypoint function's param referenced types are removed when param is not used.

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5290](https://github.com/microsoft/DirectXShaderCompiler/issues/5290).

Still reproduces on `main` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df), and on
every stable release from v1.5.2010 (2020-10) through v1.9.2607 (2026-07) --
20 releases, no exceptions. v1.4.1907 predates the rewriter's
`-remove-unused-*` options entirely and can't run this repro at all.

Both examples in the thread still reproduce exactly as quoted:

```
$ dxr -remove-unused-functions -remove-unused-globals -E ps_main repro.hlsl
float4 ps_main(VS_OUTPUT input) : SV_Target0 {
  return float4(0, 0, 0, 0);
}
```

`struct VS_OUTPUT` is gone even though `ps_main`'s own signature still names
it. The second example (unused local `Material mtl = (Material)0;`) behaves
the same way: `struct Material` (and its nested `struct LayerColor`) are
dropped too.

**Root cause:** `CollectRewriteHelper`'s `VarReferenceVisitor`
(`tools/clang/tools/libclang/dxcrewriteunused.cpp`) only marks a type "used"
when some *other* expression later reads an already-declared variable via a
`DeclRefExpr`. Declaring a variable of a type -- including the entry point's
own parameter, or a local variable that is itself never subsequently read --
is not treated as a use of that type. That's one root cause for both
examples, not two: `entryFnDecl->parameters()` is never walked for this
purpose anywhere in this file's history. A control where the variable *is*
read afterward (`return input.color;` / `return mtl.colors[0].r;`) correctly
retains the type in both cases, isolating the trigger precisely.

@Snowapril's diagnosis in the first comment (iterate `entryFnDecl->params`
and remove those types from the unused set) targets the parameter half of
this; a full fix would need the same treatment for local-variable
declarations to cover the second example.

Suggest keeping this open and adding `correctness`, since the rewriter
produces HLSL that will not recompile.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
````

### Draft — [#5292](https://github.com/microsoft/DirectXShaderCompiler/issues/5292) Rewriter : does not remove unused typedef statements and it lead to compile error

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5292](https://github.com/microsoft/DirectXShaderCompiler/issues/5292).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`dxcompiler.dll` version `1.9.0.5465 (triage, 7665270b9)`).

Running the exact repro and command from the issue through
`IDxcRewriter2::RewriteWithOptions` (the API `dxr.exe -remove-unused-functions
-remove-unused-globals -E ps_main` drives) produces:

```
typedef PSOutput PSPointOutput;
float4 ps_main(VSOutput psIn) {
  return float4(0.F, 0.F, 0.F, 1.F);
}
```

`struct PSOutput {};` is removed, `typedef PSOutput PSPointOutput;` is left
dangling — exactly as reported. Feeding that output back into `dxc -T ps_6_0
-E ps_main` confirms the claimed downstream compile error:

```
error: unknown type name 'PSOutput'
typedef PSOutput PSPointOutput;
        ^
```

**Root cause:** `CollectRewriteHelper` in
`tools/clang/tools/libclang/dxcrewriteunused.cpp` only tracks `VarDecl`s
(`unusedGlobals`), `FunctionDecl`s (`unusedFunctions`) and `TagDecl`s
(`unusedTypes`) for removal. A `TypedefDecl` is never added to any of those
sets, so it can never be considered for removal — independent of whether the
type it names survives.

**History:** reproduces on every stable release able to run this probe,
from v1.5.2010 (2020-10-22) through v1.9.2607, plus current `main`.

Related observation: the rewriter also drops `struct VSOutput {};` in every run
here, even though it's `ps_main`'s parameter type. `VarReferenceVisitor` does
not mark signature types as used unless something in the body references them.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5302](https://github.com/microsoft/DirectXShaderCompiler/issues/5302) Incorrect code for waterfall loop in VS shader

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5302](https://github.com/microsoft/DirectXShaderCompiler/issues/5302).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).

Byte-for-byte identical to the IR quoted in the issue:
`-T ps_6_0` keeps the buffer load inside the loop, guarded by `dx.break`; `-T vs_6_0` on the
*same source* hoists it out, with no `dx.break` anywhere in the output.

@simondeschenes's diagnosis is right: `CGMSHLSLRuntime::EmitHLSLCondBreak`
(`tools/clang/lib/CodeGen/CGHLSLMS.cpp`) only conditionalizes the break for `IsPS()`,
`IsCS()` and `IsLib()`. Every other stage falls through to a plain unconditional branch, so
the protection PR #2795 added never applies there. That guard is unchanged since PR #2795
introduced it on 2020-03-30 (`d3af7f123`).

History: reproduces on every stable release from v1.5.2010 (the first release to ship
`dx.break`) through v1.9.2607, and on `main-debug`. v1.4.1907 predates PR #2795, so neither
`vs_6_0` nor `ps_6_0` shows `dx.break` there; that's the mechanism being absent for every
stage, not evidence the bug wasn't happening yet.

Compiler Explorer, `vs_6_0` vs `ps_6_0` on two DXC versions: https://godbolt.org/z/jj8fzqMTK

Suggesting `correctness` and `incorrect-code` in addition to `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5309](https://github.com/microsoft/DirectXShaderCompiler/issues/5309) Dxbc to Dxil conversion failure

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5309](https://github.com/microsoft/DirectXShaderCompiler/issues/5309).

Tested against a Debug build of `main` (commit `89e2f98e2`). `dxbc2dxil`/`dxilconv` are not
executable in this environment (see below), so this is a source-level analysis rather than a
repro run.

`0x8007007e` is `HRESULT_FROM_WIN32(126)`, and Win32 error 126 is `ERROR_MOD_NOT_FOUND` ("the
specified module could not be found"). In `dxbc2dxil.cpp`, the only call that returns
`HRESULT_FROM_WIN32(GetLastError())` is `Converter::GetDxcCreateInstance`, called from
`CreateDxbcConverter` to `LoadLibraryExW(L"dxilconv.dll", NULL,
LOAD_LIBRARY_SEARCH_APPLICATION_DIR)` — and this runs **before** the DXBC bytes are ever passed
to `converter->Convert()`. A standalone harness reproducing that exact API call against a
guaranteed-missing module confirms the match:

```
LoadLibraryExW("missing", LOAD_LIBRARY_SEARCH_APPLICATION_DIR):
  GetLastError() = 126 (0x0000007E)
  HRESULT_FROM_WIN32(GetLastError()) = 0x8007007E
```

In other words, this specific error most likely means `dxbc2dxil.exe` could not find
`dxilconv.dll` next to it — not that the DXBC content failed to convert. The attached DXBC
(`0.txt`) is well-formed (correct `DXBC` fourcc, and its `TotalSize` field matches the file's
exact byte length), so the content itself doesn't look like the problem.

A plausible path is selective build/deployment: default builds put `dxbc2dxil.exe` and
`dxilconv.dll` together, but `dxbc2dxil` has no CMake dependency on `dxilconv`, so building or
copying only the `.exe` can produce this exact `0x8007007E` symptom.

This environment can't run the actual conversion to check either explanation further:
`dxilconv` isn't built here (`HLSL_BUILD_DXILCONV=OFF`, and no `dxbc2dxil.exe`/`dxilconv.dll`
exist anywhere in this build tree), and no published release ships these binaries either.

If `dxilconv.dll` was present next to `dxbc2dxil.exe` and this still failed, that would point to
a real `DxbcConverter` defect. Suggest `needs repro steps` alongside `dxilconv` to capture that
missing confirmation.

---
<sub>Triaged with AI assistance. `dxbc2dxil`/`dxilconv` are not built in this environment, so no
compiler output was produced; the evidence is source reading plus a standalone Win32 API
harness reproducing the exact error code outside any DXC build target. Please flag anything
that looks wrong.</sub>
````

### Draft — [#5328](https://github.com/microsoft/DirectXShaderCompiler/issues/5328) Typo and potential null dereference in HLMatrixBitcastLowerPass.cpp

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5328](https://github.com/microsoft/DirectXShaderCompiler/issues/5328).

Still present, unchanged, on `main` at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.
`HLMatrixBitcastLowerPass::lowerMatrix`, `lib/HLSL/HLMatrixBitcastLowerPass.cpp:244`:

```cpp
} else if (StoreInst *ST = dyn_cast<StoreInst>(U)) {
  Value *V = ST->getValueOperand();
  if (VectorType *Ty = dyn_cast<VectorType>(V->getType())) {
    IRBuilder<> Builder(LI);   // should be Builder(ST)
```

`LI` and `ST` are bound in sibling arms of the same `if`/`else if` chain,
so `LI` is guaranteed `nullptr` here: the earlier `dyn_cast<LoadInst>`
had to fail for control to reach the `StoreInst` arm. `IRBuilder<>`'s
single-`Instruction*` constructor dereferences its argument immediately
(`IP->getContext()`), so reaching this branch is an unconditional null
dereference, not a latent risk. `git blame` traces the line back past
this clone's shallow-history boundary (2025-06-03), so it's been there
at least that long.

This pass is only reachable via `dxc -T lib_6_x -link ...`
(`DxilLinker::RunPreparePass`), and I wasn't able to construct a
minimal HLSL library-link input that reaches this exact branch.
`AlwaysInlinerPass`, which runs immediately before this pass in the
same pipeline, fully inlines a cross-module call whenever the link
resolves to a single shader entry point, before a fake-matrix-typed
`Store` can ever reach this code. So the verdict here is based on the
source and the `IRBuilder` API contract, not an executed crash of this
exact branch.

Separately: the 2026-04-27 comment's attached repro does crash `main`
(confirmed, exit `0xE0000001`), but its stack trace is
`HLMatrixLowerPass::replaceAllVariableUses` → `checkGEPType`
(`lib/HLSL/HLMatrixLowerPass.cpp`) — a different file, function, and
fault from the one reported here. So it should be treated as a separate
bug, not as corroborating evidence for this typo.

Suggest adding `crash` (the code is an unconditional null dereference
once reached, not just a style issue) alongside the current
`matrix-bug`/`tech-debt`, and `shader-linking` (the bug lives entirely
in a pass that only exists for `-link`).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5338](https://github.com/microsoft/DirectXShaderCompiler/issues/5338) Arrays cast compiler error

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5338](https://github.com/microsoft/DirectXShaderCompiler/issues/5338).

**Still reproduces on `main`** (`89e2f98e2`; the local build reports
`1.9.0.5465`). A Release build hits your exact quoted text:

```
error: llvm::cast<X>() argument of incompatible type!
```

(confirmed on `dxc_trunk` via Compiler Explorer: https://godbolt.org/z/5nqjfhfve).
A Debug/assertions build instead traps @llvm-beanz's quoted assertion
word-for-word — only the source line moved (2548 → 2630):

```
Error: 	!(onlyUsedByLifetimeMarkers(BCI))
Func:	SROA_Helper::RewriteBitCast
	expected struct bitcast to only be used by lifetime intrinsics
```

Both are the same defect; which one you see just depends on whether asserts
are compiled in.

**FXC does more than avoid the error** — at `/T vs_5_0` it constant-folds the
`[unroll]` loop to `mov o1.xyzw, l(0,1,4,9)` and `mov o2.xyzw, l(16,25,36,49)`
(`n*n` for `n=0..7` across both `SV_ClipDistance` registers). DXC never
handles this input correctly: across all 21 measured releases
(v1.4.1907..v1.9.2607) plus `main`, it either hangs (v1.4.1907, rechecked at
240s), crashes (v1.7.2207 onward), or is diagnosed-rejected by validation in
between (`Not all elements of output SV_ClipDistance were written` in
v1.5.2010..v1.6.2112). That middle window is a different failure mode, not a
fix.

A candidate for the v1.6.2112→v1.7.2207 regression: `#4456` ("Fix memcpy
replacement removing memcpy to output argument") changes exactly how
`LowerMemcpy` treats `out`/`inout` parameter destinations, which is the shape
of `castFunc`'s argument here — but I did not build at that commit to confirm
it, so treat it as a lead, not an attribution.

Current labels (`bug`, `crash`, `fxc-disagrees`) all still fit; no changes
suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5350](https://github.com/microsoft/DirectXShaderCompiler/issues/5350) [SM 6.8] Reflection for Work Graph nodes plus more general DXIL Library reflection

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#5350](https://github.com/microsoft/DirectXShaderCompiler/issues/5350).

Checked `main` (`89e2f98e2`) for whether either outstanding question is already implemented. Neither is:

- `ID3D12FunctionReflection1` / `GetDesc1` / `D3D12_FUNCTION_DESC1` do not
  exist anywhere in this repository. The current
  `CFunctionReflection::GetDesc(D3D12_FUNCTION_DESC*)` fills only `Version`,
  `ConstantBuffers` and `BoundResources`; it never reads node launch mode or
  node ID.
- The data is already computed internally
  (`DxilFunctionProps::NodeProps.LaunchType`, `NodeShaderID`,
  `include/dxc/DXIL/DxilFunctionProps.h`) and serialized into RDAT for the
  runtime; reflection does not expose it.
- @damyanp's linked PR #6827 ("Added implementation for
  `ID3D12FunctionReflection1::GetDesc1`") is a concrete attempt at question 1.
  It's still open and unreviewed, and per its own description it also needs
  `D3D12_FUNCTION_DESC1` added to DirectX-Headers first.

Since both questions are still open, and there's an existing PR to react to,
suggested action is to have a maintainer weigh in on #6827 rather than
treating this as something a compiler repro could settle either way.

Suggested labels: `enhancement`, `api` (in addition to the existing
`reflection`, `sm6.8`).

---
<sub>Triaged with AI assistance. This is a design question, not something a compiler repro can settle, so the assessment above comes from reading the reflection implementation and `DxilFunctionProps` in the current source rather than from running a shader; please flag anything that looks wrong.</sub>
````

### Draft — [#5357](https://github.com/microsoft/DirectXShaderCompiler/issues/5357) Ensure type annotations are added for reference returning intrinsics/operators

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5357](https://github.com/microsoft/DirectXShaderCompiler/issues/5357).

**Still reproduces** on `main` (`89e2f98e2`), Debug build, on the shader tex3d posted here in
January 2024:

```hlsl
struct RECORD1 { uint value; };
[Shader("node")] [NodeLaunch("broadcasting")] [NodeDispatchGrid(1,1,1)] [NumThreads(128,1,1)]
void node_1_1([NodeArraySize(128)] [MaxRecords(64)] NodeOutputArray<RECORD1> OutputArray) {
    OutputArray[1].GetThreadNodeOutputRecords(2).OutputComplete();
}
```

```
$ dxc -T lib_6_8 repro.hlsl
Internal compiler error: LLVM Assert          # exit 0xE0000001
```

Under a debugger:

```
Error: assert(pAnno != nullptr && pAnno->GetNumTemplateArgs() == 1 &&
       "otherwise the node record template is not declared properly")
File:  tools\clang\lib\CodeGen\CGHLSLMSFinishCodeGen.cpp(1071)
Func:  AddOpcodeParamForIntrinsic
```

That is exactly the function and file anupamachandra named in this thread. `pAnno` is null
because chaining `GetThreadNodeOutputRecords(2)` straight into `.OutputComplete()` — with no
bound local in between — is the shape that skips the type-annotation path, as the issue
describes. Binding the intermediate result first (`ThreadNodeOutputRecords<RECORD1> outRec =
...; outRec.OutputComplete();`, the shape every existing test uses) compiles cleanly.

**Not Debug-only.** The check compiled out under `NDEBUG` still leaves the null flowing on:
every catalogued stable release that supports `lib_6_8` (`v1.8.2403` through `v1.9.2607`) takes
an access violation instead (`Internal compiler error: access violation. Attempted to read
from address 0x0000000000000028`), and [Compiler Explorer](https://godbolt.org/z/eqjMv4v5Y)
shows the same fault on Linux `dxc_trunk` as `SIGSEGV`. Releases predating `v1.8.2403` reject
`lib_6_8` outright (`error: invalid profile lib_6_8` — Work Graphs didn't exist yet), so this
has reproduced for as long as the feature has been checkable.

PR [#6227](https://github.com/microsoft/DirectXShaderCompiler/pull/6227) ("Fixes: #5357") has
been open in draft, with its own "TODO: Add tests" unaddressed, since January 2024 and is still
unmerged.

Suggested labels: add **`bug`** and **`crash`** — this is a reproducing internal crash, not
only prospective tech debt. Keep `tech-debt`, since the issue's broader ask (auditing every
reference-returning intrinsic/operator for the same gap) remains open beyond this one confirmed
instance.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5389](https://github.com/microsoft/DirectXShaderCompiler/issues/5389) `as` casts on integer constant swizzles result in invalid module bitcode (or assert in debug)

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5389](https://github.com/microsoft/DirectXShaderCompiler/issues/5389).

Still reproduces on `main` (Debug build, commit
[89e2f98](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df)).

Reporter's minimal repro
([comment](https://github.com/microsoft/DirectXShaderCompiler/issues/5389#issuecomment-2332351850)):

```hlsl
RWByteAddressBuffer sb : register(u0);
[numthreads(1, 1, 1)]
void main() {
  sb.Store(0, asuint(int2(123, 123))); // Okay
  sb.Store(0, asuint((123).xx)); // Boom
}
```

- On a Debug (assert-enabled) build, trips the `CallInst::init` "Calling a function with a
  bad signature!" assert.
- On every stable release binary from v1.4.1907 through v1.9.2607, and on today's Compiler
  Explorer `dxc_trunk`, the assert is compiled out and the malformed call instead fails DXIL
  validation (`Invalid record` / `Validation failed.` — CE's older `dxc_1_6_2112` prints a
  differently-worded but equivalent diagnostic, `Call parameter type does not match function
  signature!`).
- Linear scan of all 20 probeable stable releases (v1.4.1907..v1.9.2607): repros on all 20; no
  invalid probes.

[Compiler Explorer link](https://godbolt.org/z/Y45Yhd3P5) — 4 panes over the same source:
default mode fails on both `dxc_1_6_2112` and current `dxc_trunk`. `-HV 2021` also still
fails and is not a workaround; only the still-experimental `-HV 202x` preview mode compiles
clean.

Separately, #5082 (filed earlier, same underlying bare-literal-swizzle-into-fixed-width-arg
defect at a different call site) was closed on the same "fixed in HLSL 202x" reasoning
(2024-08-28); this issue later got pushback on that same reasoning (2024-09-10) and was
marked dormant instead (2024-09-12). Noting the difference for awareness, not proposing
either be revisited.

Suggested labels: `crash` (the Debug-build assert), `type-system` (the likely root-cause
area — literal constant-folding/typing across a swizzle), `hlsl-next` and `up-for-grabs` (per
the maintainer's own framing: fixed by the language change, and a targeted codegen fix would
be reviewed).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5395](https://github.com/microsoft/DirectXShaderCompiler/issues/5395) Report warning when loop variable shadows one from outer scope in HLSL 2021

````markdown
> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5395](https://github.com/microsoft/DirectXShaderCompiler/issues/5395).

Confirmed: still reproduces on `main` (Debug build, commit `89e2f98e2`, 2026-08-19). Compiling
the repro with `-T ps_6_6 -HV 2021` produces no `-Wfor-redefinition` warning, while the
identical source under `-HV 2018` still does:

```
repro.hlsl:6:18: warning: redefinition of 'i' shadows declaration in the outer scope; most recent declaration will be used [-Wfor-redefinition]
       for (uint i = 0; i < 3; i++) {
                 ^
```

This reproduces on every DXC release that has ever supported `-HV 2021` -- v1.6.2112
(2021-12-08, the release that added the flag) through v1.9.2607, and `main`. It is not a
regression: the warning is tied to a `-HV`-gated `Scope::ForDeclScope` marker
(`ParseStmt.cpp`) that made the pre-2021 for-loop variable leak into, and merge with, the
enclosing scope's declaration of the same name -- `warn_hlsl_for_redefinition` exists to
soften what would otherwise be a same-scope `redefinition` error. HLSL 2021 gives the loop
variable a real nested scope instead, so there is no same-scope redefinition event left for
that diagnostic to describe.

More generally, DXC has no `-Wshadow`-style diagnostic for ordinary block-scope shadowing in
*either* language mode -- an inner `{ }` block redeclaring an outer variable produces no
warning under `-HV 2018` either. So this isn't a case of an existing check losing its target;
resolving it would mean adding a new shadow diagnostic for HV2021+ scoping, not restoring old
behavior.

Compiler Explorer (`dxc_1_6_2112`, `dxc_trunk`): https://godbolt.org/z/KzYb6cKTE -- both
compile clean, no warning.

Suggest adding the `diagnostic` label alongside the existing `bug`/`hlsl2021` -- this is
squarely a diagnostic-coverage question. Whether it should stay `bug` or move to
`enhancement` is a maintainer call: nothing regressed, but adding shadow detection for the new
scoping rules seems like a reasonable ask.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5416](https://github.com/microsoft/DirectXShaderCompiler/issues/5416) depfile generation isn't supported in the same invocation as compilation

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5416](https://github.com/microsoft/DirectXShaderCompiler/issues/5416).

Still reproduces on `main` (commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df)).

Your exact command line, run against an ordinary valid `lib_6_7` shader: exits 0, prints
nothing, writes `source.d`, and never writes `source.cso`. Without `-MD -MF` the same shader
compiles to a normal object file.

Root cause, in `DxcContext::ActOnBlob` (`tools/clang/tools/dxclib/dxc.cpp`):

```cpp
if (m_Opts.DumpDependencies) {
  // ...writes the depfile...
  return retVal;                    // <-- returns here
}
// Write the output blob.
if (!m_Opts.OutputObject.empty()) { // <-- -Fo is handled here, never reached
```

Any of `-M`, `-MD`, `-MF` makes the compiler take a preprocess-only path and return
immediately after writing the depfile, before the `-Fo` write ever runs — regardless of whether
the shader is valid. This has been the case since `-M`/`-MD`/`-MF` were added
([#4017](https://github.com/microsoft/DirectXShaderCompiler/pull/4017), Dec 2021): every stable
release since (`v1.7.2207` through `v1.9.2607`, 15 releases) reproduces it, plus a local
`main-debug` build, with zero clean releases in between. Releases before that reject `-MD` outright with `Unknown argument: '-MD'`.

Compiler Explorer's `dxc_trunk` shows the same thing on the identical command —
`<No output file>` at exit 0:
https://godbolt.org/z/3jn1eM9K4

This is a different visible symptom from the same code path as
[#5117](https://github.com/microsoft/DirectXShaderCompiler/issues/5117) (which loses a
diagnostic for *invalid* source under `-MD`/`-MF`) — fixing that one wouldn't by itself restore
the `-Fo` output here, since the early return happens unconditionally. It's also distinct from
[#4723](https://github.com/microsoft/DirectXShaderCompiler/issues/4723), which is specifically
about `-MD`/`-MF` combined with `-P`.

Suggest keeping `bug` and `high-impact`, and adding `diagnostic` — the compiler gives no
indication at all that the requested `-Fo` output was skipped.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5417](https://github.com/microsoft/DirectXShaderCompiler/issues/5417) Attributes read via `GetAttributeAtVertex` aren't counted as read in the signature

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5417](https://github.com/microsoft/DirectXShaderCompiler/issues/5417).

Still reproduces on current `main` (89e2f98e2). Compiling the reported shader
with `-DUSE_GET_ATTRIBUTE_AT_VERTEX` still leaves the `COLOR` row's `Used`
column blank while `Mask` is `xyzw`:

```
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; COLOR                    0   xyzw        0     NONE   float
```

The same source compiled without the define shows `Used` as `xyzw` for the
identical row, so this is specific to reads through `GetAttributeAtVertex`.

Reproduces on every cached stable release back to v1.4.1907 (2019-07,
`ps_6_1`/`GetAttributeAtVertex` already usable there), through v1.9.2607, and
on Compiler Explorer's oldest DXC (`dxc_1_6_2112`) and `dxc_trunk`:
https://godbolt.org/z/zWTG5Wrxv. No release ever marks this input used.

Source-level cause: `MarkUsedSignatureElements`
(`lib/HLSL/DxilPreparePasses.cpp`) computes the `Used` mask by scanning for
`LoadInput`/`StoreOutput`/`LoadPatchConstant`/`StorePatchConstant` and their
vertex/primitive variants -- it never looks at `AttributeAtVertex`
(`dx.op.attributeAtVertex`), even though the disassembly shows the entry point
does call it and forwards every result to `storeOutput`. The value is fully
lowered and used; this one pass just never checks that opcode.

Given @tex3d's confirmation that this mask feeds inter-stage signature
validation, and that the original motivation was reflecting on which inputs
survive dead-code elimination, suggest adding the `reflection` label
alongside the existing `bug`/`correctness`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5423](https://github.com/microsoft/DirectXShaderCompiler/issues/5423) `dxr.exe` doesn't support macro definitions via its CLI

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5423](https://github.com/microsoft/DirectXShaderCompiler/issues/5423).

Still reproduces on `main` (dxcompiler.dll self-reports commit `89e2f98e2`).

- `dxc -T ps_6_0 -E PSMain -D float4=0 repro.hlsl` still fails with
  `error: expected member name or ';' after declaration specifiers` — confirming `-D`
  expansion itself works fine. [Compiler Explorer](https://godbolt.org/z/GzETMvxvs).
- `dxr -D float4=0 -E PSMain repro.hlsl` still exits 0 with no error or warning and leaves
  `float4` unsubstituted. Same `-D`-ignoring behavior across all 20 cached stable releases,
  `v1.4.1907` through `v1.9.2607` (plain `-D float4=0 -E PSMain`), and, on the current build
  only, also with `-decl-global-cb` and `-line-directive` added.

Root cause: `tools/clang/tools/dxr/dxr.cpp` calls
`RewriteWithOptions(pSource, wName.c_str(), argv_, argc, nullptr, 0, ...)` — it always passes
`nullptr, 0` for `RewriteWithOptions`'s separate defines parameter. `-D` is parsed into
`opts.Defines` from `argv_` inside that call, but the parsed value is never forwarded to the
rewrite functions (`DoRewriteGlobalCB`, `DoReWriteWithLineDirective`, `DoSimpleReWrite`), which
use only the always-empty `pDefines`/`defineCount` pair.

#5424 already implements the fix (pass `opts.Defines.data()/size()` at those three call
sites) and adds a FileCheck test matching the diagnostic above. It was never merged — a
reviewer raised an open design question about interactions with `#ifdef`-driven
`-remove-unused-globals` (see #4357), and the thread stopped there; the PR was closed in 2026
as inactive, not as rejected.

Suggest keeping this open pending that product decision, rather than closing as fixed or
stale.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5434](https://github.com/microsoft/DirectXShaderCompiler/issues/5434) [Validation] Add validation for Annotate\*Handle intrinsics

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#5434](https://github.com/microsoft/DirectXShaderCompiler/issues/5434).

Still reproduces on `main` (1.9.0.5465, `89e2f98`): `AnnotateHandle`, `AnnotateNodeHandle`
and `AnnotateNodeRecordHandle` accept a handle operand that was never derived from any
`Create*Handle` call, and the validator raises nothing.

No HLSL repro is possible here — a normal compile always CodeGens a matching create/annotate
pair — so this is measured with hand-written DXIL fed straight to the standalone validator
(`dxv`), not Compiler Explorer:

```
$ dxv variant-annotatehandle-zero.ll
Validation succeeded.
```

Feeding the identical zero/undef handle to an ordinary checked opcode instead
(`BufferUpdateCounter`) is correctly rejected, so this isn't zero/undef handles being
silently accepted everywhere in the module — it's specific to these opcodes:

```
$ dxv control-bufferupdatecounter-zero.ll
error: Instructions should not read uninitialized value.
Validation failed.
```

`DxilValidation.cpp`'s `ValidateHandleArgs` still names the gap explicitly:

```cpp
case DXIL::OpCode::AnnotateHandle:
case DXIL::OpCode::AnnotateNodeHandle:
case DXIL::OpCode::AnnotateNodeRecordHandle:
case DXIL::OpCode::CreateHandleForLib:
  // TODO: add custom validation for these intrinsics
  break;
```

That TODO was added by #5399 (2023-07-21), three days after this issue was filed, as a
deliberate carve-out while implementing item 1 of #5356 for every other handle-consuming
opcode. It is unchanged today, and the same gap is present in the tested release (v1.8.2502)
as well as on `main` — this was never implemented rather than having regressed, so there's no
fixed-in/regressed-in release to point to.

Current labels (`enhancement`, `tech-debt`, `validation`) already describe this well; no
changes suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5436](https://github.com/microsoft/DirectXShaderCompiler/issues/5436) [Validation] Add an assert to make sure no dxil opcodes are left unvalidated.

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5436](https://github.com/microsoft/DirectXShaderCompiler/issues/5436).

Still unaddressed on `main` (89e2f98e2). Neither function has the requested assert or a
comment justifying its absence:

`ValidateDxilOperationCallInProfile`'s opcode switch (`lib/DxilValidation/DxilValidation.cpp`):

```cpp
  default:
    // TODO: make sure every Opcode is checked.
    // Skip opcodes don't need special check.
    break;
  }
}
```

`ValidateHandleArgs`'s opcode switch (the function that now wraps
`ValidateHandleArgsForInstruction`):

```cpp
  default:
    ValidateHandleArgsForInstruction(CI, Opcode, ValCtx);
    break;
  }
}
```

The second one isn't a no-op — every opcode not in the four excluded cases still gets
`ValidateHandleArgsForInstruction`'s generic handle-argument checks — so it's closer to
the "prove it's safe and comment why" alternative this issue offers. But there's still no
comment recording that reasoning and no assert either, so the ask (an explicit signal
either way) is unmet for both functions.

For context: this is the issue @bob80905 linked from a PR #5982 review thread
(2023-11-08) in reply to a maintainer's "Do we have an issue tracking this?" on the same
switch — so it's a confirmed, still-open gap, not a stale one-off suggestion.

This isn't something a shader repro or a Compiler Explorer link can demonstrate: an
opcode silently skipped by an empty default produces identical `dxc` output whether or
not the assert exists (asserts don't affect codegen), so there's nothing to compile that
would show the gap either way. No CE link is included for that reason.

Labels (`enhancement`, `tech-debt`, `validation`) still look right; no change suggested.

---
<sub>Triaged with AI assistance. This assessment was produced by reading the current
source directly; please flag anything that looks wrong.</sub>
````

### Draft — [#5448](https://github.com/microsoft/DirectXShaderCompiler/issues/5448) [Validation] Organize usage of GetResourceFromHandle and GetResourceFromVal calls in validation

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5448](https://github.com/microsoft/DirectXShaderCompiler/issues/5448).

Confirmed still current on `main` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):
`GetResourceFromHandle` (`lib/DxilValidation/DxilValidation.cpp`) still both
looks up resource properties and emits `InstrHandleNotFromCreateHandle` as a
side effect, and `GetSamplerKind`, `GetResourceKindAndCompTy` and
`GetCBufSize` still all call it rather than the silent `GetResourceFromVal`.
Since the up-front handle-argument pass from #5399 and these per-op
accessors both run against the same operand with no early return between
them, an invalid handle reaching e.g. `GetDimensions` can still emit
`InstrHandleNotFromCreateHandle` twice. No `ValidateResourceHandle`
function exists, and `DxilResourceProperties::isValid()` is never called
from the validator — every call site still hand-repeats
`getResourceClass() == Invalid`.

Worth noting: `ValidateASHandle` (for `TraceRay`'s acceleration-structure
handle) already uses exactly the pattern this issue asks for everywhere —
`GetResourceFromVal` plus a manual validity check and a single specific
diagnostic — so both styles already coexist, and the target pattern is
already proven out in this file.

No `dxc.exe` command line or Compiler Explorer link is included: this is a
request to reorganize validator source, and the one observable consequence
(a duplicate diagnostic) needs a resource handle that isn't a recognised
`CreateHandle` result reaching a resource op. Ordinary HLSL can't construct
that — dxc's own legalizer rejects a dynamically-selected resource handle
(`local resource not guaranteed to map to unique global resource`) before
DXIL validation ever runs, confirmed directly against a control shader that
selects between two `Texture2D` locals.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
````

### Draft — [#5476](https://github.com/microsoft/DirectXShaderCompiler/issues/5476) [MacOS only] dxc dump nothing when -fcgl with root signature

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5476](https://github.com/microsoft/DirectXShaderCompiler/issues/5476).

Tested against `main` at `13730886e` (2026-08-12): the reported symptom is
platform-specific and could not be directly re-confirmed or refuted, but a
plausible fix candidate has landed since llvm-beanz's last "still reproduces" comment.

**Why this can't be re-confirmed directly.** The bug is in the *nix-only
emulation of `MultiByteToWideChar` (`lib/DxcSupport/Unicode.cpp`), which
Windows never runs (Windows uses the real Win32 API). On Windows, the exact
repro compiles cleanly and prints the complete `-fcgl` dump, including the
root signature bytes — expected, and not evidence either way. Compiler
Explorer's Linux-hosted DXC *does* run the *nix code path, but both the
oldest available build (`dxc_1_6_2112`, Dec 2021) and current `dxc_trunk`
also print the complete dump cleanly
([godbolt](https://godbolt.org/z/vajbo9sxW)) — including on the four-year-old
build that clearly predates any fix. That means CE's own environment never
had the failing locale condition to begin with, so it can't corroborate a
fix boundary here either.

**A plausible fix candidate.** `9bcce409b` ("Fix potential unicode conversion issues for
*nix", #7506, merged 2025-11-25) rewrites exactly this code: `ScopedLocale`
used to call `setlocale(LC_ALL, "en_US.UTF-8")` process-globally with no
check that it succeeded, and the *nix `MultiByteToWideChar` emulation had no
explicit handling for an `mbstowcs` failure. The commit switches to
thread-local `uselocale`/`newlocale` and adds explicit failure detection —
the exact class of "silent Unicode conversion failure on *nix" this issue
describes. It isn't referenced by this issue anywhere, so the connection is
inferred from the code and the timing, not confirmed by testing on an
affected machine (none was available for this triage).

Note: the workaround patch posted in this thread (skip the UTF-8 round trip
on Linux/macOS) was never merged; `WriteUtf8ToConsole` still round-trips
through `UTF8BufferToWideBuffer` on every platform. The fix, if it is one,
came from repairing that conversion rather than bypassing it.

Suggest keeping this open with `bug`, `macos`, `usability` (all still
accurate) until someone can rebuild and test on macOS/Linux against a
compiler containing `9bcce409b` — that's the missing confirmation.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
````

### Draft — [#5481](https://github.com/microsoft/DirectXShaderCompiler/issues/5481) [Build] enable clang Source Based Code Coverage on windows

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5481](https://github.com/microsoft/DirectXShaderCompiler/issues/5481).

This is a build/CI request rather than a compiler bug, so there's no shader or `dxc.exe`
command line to test — the checks below come from reading the CMake and CI scripts at
`main` (89e2f98e2).

**Still open, and a matching fix was proposed and closed unmerged.** #5510, opened by the
same reporter a week after this issue, tried to fix exactly this:

```
1. Use PYTHON_EXECUTABLE instead of Python3_EXECUTABLE which not enabled for DXC.
2. Use "" instead of '' for -fprofile-instr-generate=${LLVM_PROFILE_FILE_PATTERN
```

It closed without merging, and its target lines are unchanged on `main` today:

- `cmake/modules/HandleLLVMOptions.cmake` still appends
  `-fprofile-instr-generate='${LLVM_PROFILE_FILE_PATTERN}' -fcoverage-mapping` with single
  quotes, which a Windows/clang-cl command line does not strip the way a Unix shell does.
- `cmake/modules/CoverageReport.cmake`'s `generate-coverage-report` target still invokes
  `${Python3_EXECUTABLE}`, not `${PYTHON_EXECUTABLE}`.
- `.github/workflows/coverage-gh-pages.yml` (the only coverage-generating CI job) still runs
  only on `ubuntu-latest`, and `cmake/caches/PredefinedParams.cmake` — the cache script that
  wires up `-DDXC_COVERAGE=On` — still documents itself as being "for building DXC using
  CMake on *nix platforms."

Nothing in `HandleLLVMOptions.cmake` blocks setting `LLVM_BUILD_INSTRUMENTED_COVERAGE=ON` on a
Windows configure directly, but nothing here confirms that path has ever been exercised
end-to-end either; the CI job and the maintained cache script both remain Linux-only, and #5510
is the one attempt on record to make it work.

Labels: `enhancement` and `build` both still fit. Consider adding `ci`, since the concrete gap
is a CI workflow and its cache script rather than general build plumbing.

---
<sub>Triaged with AI assistance. This assessment is based on reading the build/CI scripts and
the linked PR, not on running a compiler; please flag anything that looks wrong.</sub>
````

### Draft — [#5491](https://github.com/microsoft/DirectXShaderCompiler/issues/5491) DXC does not eliminate wave intrinsic calls even when the result is unused

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5491](https://github.com/microsoft/DirectXShaderCompiler/issues/5491).

Still reproduces on `main` (built at the public commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`) and on every stable release checked back to
v1.4.1907 (2019-07) — this has never behaved differently. Compiler Explorer, both DXC's oldest
build and current trunk: <https://godbolt.org/z/1T6e4zWsf>

```llvm
define void @main() {
  %1 = call i32 @dx.op.loadInput.i32(i32 4, i32 0, i32 0, i8 0, i32 undef)
  %2 = call i32 @dx.op.waveReadLaneFirst.i32(i32 118, i32 %1)  ; WaveReadLaneFirst(value)
  ret void
}
```

`%2` is never referenced before `ret void` — the same shape reported in 2023.

**Why the call survives DCE:** `dx.op.waveReadLaneFirst` (like every wave/quad intrinsic in
`DxilOperations.cpp`) is declared with no `readnone`/`readonly` attribute, only `nounwind`
(visible in this build's own disassembly: `declare i32 @dx.op.waveReadLaneFirst.i32(i32, i32)
#1` / `attributes #1 = { nounwind }`). Ordinary LLVM DCE only removes an unused call to an
external function it can prove has no side effects, so a plain `nounwind` declaration is never
eligible, regardless of whether the caller uses the result.

That reads as deliberate conservatism rather than an oversight: a wave op's result depends on
which lanes are active at that program point, so treating it as an ordinary pure value that can
be freely deleted is not obviously safe in general — which is the same concern raised in this
thread already (*"I'm not convinced there isn't a correctness bug lurking here too"*). DXC does
have a separate mechanism that deletes a wave op when it can prove the surrounding control-flow
region is dead (`EraseDeadRegion`, exercised by
`wave_intrinsic_dead_loop.hlsl`), but that is a different, narrower proof than "this call's
result value happens to be unused," which is what this issue asks for. The linked PR #5559 is
unmerged and is itself a workaround for that other mechanism over-deleting a wave op it should
have kept — evidence the surrounding design space is still being worked out, not that this case
has been addressed.

No label change proposed — `bug`, `performance`, `dxil` already fit: a real, longstanding
missed optimisation rather than a correctness defect in what is currently emitted.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

### Draft — [#5546](https://github.com/microsoft/DirectXShaderCompiler/issues/5546) [Doc Update Request] Clarify the `discard` statement as *not* a control flow statement

````markdown
> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5546](https://github.com/microsoft/DirectXShaderCompiler/issues/5546).

DXC output supports the compiler-behavior claim. Two otherwise-identical pixel shaders differ
only inside `if (pos.x < 0) { ... }`:

```hlsl
// A: discard;
// B: return float4(0,0,0,0);
```
```hlsl
buf[0] = 42;          // RWStructuredBuffer<uint>
return float4(1,1,1,1);
```

`discard` (`-T ps_6_0`, DXIL):

```
call void @dx.op.discard(i32 82, i1 true)
br label %5
; <label>:5           ; preds = %4, %0
call void @dx.op.bufferStore.i32(... i32 42 ...)     ; reached from BOTH arms
call void @dx.op.storeOutput.f32(... 1.0 ...)        ; unconditional, x4
```

`return` (same command, same structure otherwise):

```
br i1 %3, label %5, label %4
; <label>:4           ; preds = %0 (only when NOT taking the early exit)
call void @dx.op.bufferStore.i32(... i32 42 ...)     ; SKIPPED on the early-return arm
br label %5
```

`discard` reaches the write/output block from both branch arms. `return` reaches the write
block from one arm, so the early-return arm skips it. `discard` is a non-terminating intrinsic
that falls through; it does not jump past later statements the way the
[Flow Control](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-flow-control)
page's own definition ("jump...to an instruction other than the one on the next line")
describes. Any UAV/export elision happens after this compiled control flow, not as a branch
here.

That Learn page (last updated 2025-03-11) still groups `discard` in the same bullet list as
`break`/`continue`/`do`/`for`/`if`/`switch`/`while` as of this writing, so the reported text
hasn't changed.

Scope note: that page is not in this repository (`original_content_git_url` ->
`github.com/MicrosoftDocs/win32-pr`), so edit requests belong there; this repo can only confirm
compiler behavior.

Same shape holds on Compiler Explorer's oldest published DXC (1.6.2112) and on trunk:
https://godbolt.org/z/rnEKhGWcY

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5554](https://github.com/microsoft/DirectXShaderCompiler/issues/5554) C++11 enums don’t work as integer constants as expected

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5554](https://github.com/microsoft/DirectXShaderCompiler/issues/5554).

Still reproduces on `main` (commit `89e2f98e2`).

This thread narrowed a few times, so here's where it landed. The array-index half of the
original report (`partiboi[KEK::WAIT]` without a cast) is **not a bug** — real C++ rejects the
identical construct too, because a scoped enum doesn't implicitly convert to an integer for
subscripting; adding the cast, as the thread itself found, is correct.

The part that is still broken: a scoped enum's enumerator is not accepted as a non-type
template argument even when the template parameter's declared type is that exact enum type
(no conversion in question at all):

```
error: non-type template argument of type 'ENUM' is not an integral constant expression
```

The identical pattern with a plain (unscoped) `enum` compiles cleanly, and gcc accepts the
scoped-enum version outright (`-std=c++17`) — so this is a DXC-specific gap, not intended
behavior. Link with both DXC panes and a Clang pane for comparison:
https://godbolt.org/z/bqbP386nM

This is a duplicate of #6706, where a maintainer already stated: "we're not planning on
investing in fixing this in DXC. This won't be an issue in clang." That prediction now has
direct confirmation — the linked `hlsl_clang_trunk` pane compiles the same pattern cleanly.

One more thing worth flagging: the later comment linking
`godbolt.org/z/EGaesxvE1` ("concepts like `integral_constant<Enum,EnumVal>` are busted") uses
a **plain** enum in that specific link, which does compile — the underlying defect is real, but
that particular posted repro doesn't demonstrate it.

Labels: keeping `bug` and `hlsl2021`; adding `type-system` — DXC's constant-expression
evaluator not treating a scoped-enum enumerator as an integral constant expression in this
position is exactly that kind of inconsistency.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5563](https://github.com/microsoft/DirectXShaderCompiler/issues/5563) "found unregistered decl" when compiling partial template specialization for SPIR-V

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5563](https://github.com/microsoft/DirectXShaderCompiler/issues/5563).

This is fixed on current `main` (source-equivalent to
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`; the local Debug binary self-reports
`7665270b9`). The filed command (`-T ps_6_0 -E PSMain -spirv -HV 2021`) now
exits 0 and emits valid SPIR-V; forcing `-Od` so the optimizer cannot simply
eliminate the unused local confirms the static member reference is correctly
resolved to `true` rather than the fatal error just being dead-code-eliminated
away.

Stable-release testing places the fix in **v1.9.2602**: `v1.8.2505.1` still
fails with the exact reported diagnostic (`found unregistered decl`, same
source location, exit `0x80004005`), while `v1.9.2602` compiles successfully.
[Compiler Explorer](https://godbolt.org/z/Y1W7q714v) shows the same contrast:
dxc 1.6.2112 fails with the reported error, trunk succeeds.

The most likely fix is
[`1e3da156b`](https://github.com/microsoft/DirectXShaderCompiler/commit/1e3da156b7aeab25b7e891010e579902322845ed)
("Handle partial template class specialization", #7673), which stopped the
SPIR-V backend from generating code directly off the un-instantiated partial
specialization decl. It also fixed #7007, an independently filed near-duplicate
with the identical diagnostic text on a different template. A second commit
in the same window,
[`b9af1ec44`](https://github.com/microsoft/DirectXShaderCompiler/commit/b9af1ec44364a5d359af82bee5adce7ee7fca76a)
("Folding global constant variables", #7786), also touches the exact code path
that raised this error and may have contributed. Both are confirmed by commit
ancestry to fall inside the `v1.8.2505.1` → `v1.9.2602` window; neither was
verified by building and testing the commit in isolation, so treat the
attribution as strong rather than certain.

The existing `bug` and `spirv` labels remain accurate; no label change is
suggested. The issue can be closed as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5567](https://github.com/microsoft/DirectXShaderCompiler/issues/5567) -Wcomma-in-init should maybe be more aggressive?

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5567](https://github.com/microsoft/DirectXShaderCompiler/issues/5567).

Still reproduces on `main` (main-debug, `89e2f98e2`). `dxc -T cs_6_6 repro.hlsl -Od`
on

```hlsl
[numthreads(1, 1, 1)]
void main()
{
  uint2 a = (1, 2) / 2;
}
```

compiles clean with no `-Wcomma-in-init` diagnostic. The same comma pair with no
division, `uint2 a = (1, 2);`, still gets the warning on the identical build, so the
check itself is intact — it just doesn't look inside `firstArg` for a comma
expression, only at `firstArg` itself
(`SemaHLSL.cpp`, `IsExpressionBinaryComma`/`warn_hlsl_comma_in_init`). That has been
this narrow since before this repository's oldest history is checkable; a 20-release
scan (`v1.4.1907`..`v1.9.2607`, `v1.6.2104` the oldest that supports `cs_6_6`) never
reproduced anything else.

@damyanp's comment above is confirmed on a fresh check: `hlsl_clang_trunk` on
[Compiler Explorer](https://godbolt.org/z/dPM8vnz5b) does flag this shape today,
via `-Wunused-value` ("left operand of comma operator has no effect") rather than a
dedicated `-Wcomma-in-init`-style check — a more general diagnostic that happens to
catch the same mistake.

Suggested: keep `enhancement`, `diagnostic` — this is a real, still-open gap in
`-Wcomma-in-init`'s coverage, not a bug in generated code.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5573](https://github.com/microsoft/DirectXShaderCompiler/issues/5573) "External declaration [decl name] is unused" after resource assignment

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5573](https://github.com/microsoft/DirectXShaderCompiler/issues/5573).

Still reproduces on `main` (Debug build, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), and on every stable release
that can even express this shader — `v1.6.2104` (2021-04-20, the first release with
`ResourceDescriptorHeap`/`cs_6_6`) through `v1.9.2607` (2026-07-29). `v1.4.1907` and
`v1.5.2010` reject the profile itself (`error: invalid profile cs_6_6`) and predate the
feature, so they're not evidence of a fix, just of the feature not existing yet.

Compiler Explorer, both CE's oldest DXC and current trunk, same result:
https://godbolt.org/z/r6TGKo7sv

```
error: validation errors
<source>:1: error: External declaration '\01?buffer@@3URWByteAddressBuffer@@A' is unused.
Validation failed.
```

The root cause: `DxilCondenseResources.cpp`'s `UpdateResourceSymbols` asserts
`GV->user_empty()` before replacing a resource's DXIL symbol with `undef`, on the assumption
that the resource's global variable has already been fully lowered away. When `buffer` is
used *before* being reassigned to a `ResourceDescriptorHeap` handle, that assumption is false
— the global still has a real user (the earlier `Store`) — and in a Debug build the assert
traps (confirmed by a local build: `Internal compiler error: Terminal Error 0x80000003`,
`!(GV->user_empty())`, `DxilCondenseResources.cpp:1984`). Release builds compile the assert
out, so execution falls through: the resource's DXIL symbol still gets replaced with
`undef`, the now-stale global is left behind, and the validator reports it as unused —
exactly this issue's symptom. Both are the same defect; only the build configuration decides
which face you see. The assert itself predates Shader Model 6.6 by about four years
(`dc3ad5efe`, 2018), so it was never written to guard this pattern specifically.

A control that uses `ResourceDescriptorHeap` alongside a static resource, without the
reassign-then-reuse pattern, compiles cleanly — this is specific to reassigning a resource
variable that was already used, not to mixing static and dynamic resources in general.

@llvm-beanz's root-cause read in the earlier comment still holds, and the open design
question raised there — whether reassigning a global resource declaration should be
diagnosed at compile time rather than silently mis-compiled — remains unresolved.

Suggested labels: no change (`bug`, `dxil`, `correctness` already fit).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5587](https://github.com/microsoft/DirectXShaderCompiler/issues/5587) Bitfield initialization unclear

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5587](https://github.com/microsoft/DirectXShaderCompiler/issues/5587).

This no longer reproduces on `main` (commit `89e2f98e2`; local build
metadata points to a fork-local merge commit, but the compiler source
tree matches public `89e2f98e2`).

`SomeBitfield val = (SomeBitfield)0;` now compiles cleanly with
`-T cs_6_6 -HV 2021`, in both the field order reported as failing
(`SomeEnum field1 : 2; uint32_t rest : 30;`) and the reordered form the
issue said worked. The generated DXIL stores a concrete `0` into the
struct's storage word (not `undef`):

```
call void @dx.op.rawBufferStore.i32(i32 140, %2, i32 0, i32 0, i32 0, i32 undef, i32 undef, i32 undef, i8 1, i32 4)
```

Bisecting the public releases: it still failed with the exact reported
diagnostic through v1.8.2502 (2025-02-20) —

```
error: cannot convert from 'literal int' to 'SomeBitfield'
```

— and is clean at v1.8.2505 (2025-05-24). (v1.4.1907 through v1.6.2106
cannot probe this because `-HV 2021` is unsupported.)
[Compiler Explorer](https://godbolt.org/z/xG8Kj4v58) shows the same
contrast: CE's oldest DXC (1.6.2112) fails, `dxc_trunk` compiles.

The order-dependence appears resolved: both member orderings now behave
the same.

The broader design question raised in this thread (should HLSL adopt
C/C++ aggregate-initialization rules, e.g. `SomeBitfield val = {};`)
is untouched by this fix and remains open per the linked
`hlsl-specs` proposal/issue.

Suggested labels: no change (`bug`, `hlsl2021`).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5595](https://github.com/microsoft/DirectXShaderCompiler/issues/5595) [Feature Request] support hash stability test in lit

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5595](https://github.com/microsoft/DirectXShaderCompiler/issues/5595).

Checked against `main` at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`. This is a
test-infrastructure request, so there's no shader repro to run — the finding comes from the
repository and its history instead.

**Still open, and the text is accurate: no lit-native hash-stability mechanism exists in
`main` today.** `tools/clang/test/HLSLFileCheckLit` (the lit side) has 29 tracked files and
none carries a hash-stability check; `tools/clang/test/HLSLFileCheck` (the TAEF side, where
the 10 `CodeGenHashStability*` tests run today) has 2212. `utils/lit/lit/formats/` has no
hash-related format.

There was an attempt: PR #5600, "[lit] Add hash stability test for lit.", opened the same
day as this issue and explicitly "Fixes #5595". It added a `DxcHashTest` lit format that
compiled each shader twice (with/without `-Zi`) and compared container hashes. It got three
weeks of substantive review, including a design objection from the reviewer that was never
resolved — that the new format doesn't traverse using the normal lit shell-test flow and
doesn't respect local configs the way expected, which surfaced two real hash mismatches that
got worked around (two tests disabled) rather than fixed. The PR's last commit is from
2023-09-22; it has had no further commits since, and `gh pr view` reports it's still open
and unmerged (confirmed directly: its head commit is not an ancestor of `main`).

A related duplicate, #5552, was filed nine days earlier and closed in favor of this one.

So the ask here is unchanged and still valid, and there's a concrete, reviewed starting
point (PR #5600) that stalled on one design question rather than being abandoned outright.

Suggest: keep open (`still-valid-keep-open`); worth flagging as `up-for-grabs` given #5600's
review history already narrows down what a mergeable version needs to fix.

---
<sub>Triaged with AI assistance. This finding is based on repository/PR history rather than
a compiler run; please flag anything that looks wrong.</sub>
````

### Draft — [#5632](https://github.com/microsoft/DirectXShaderCompiler/issues/5632) Can construct-cast an array type to non-array without compiler complaining (DXIL Crash)

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5632](https://github.com/microsoft/DirectXShaderCompiler/issues/5632).

Still reproduces on `main` (public commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`) and on
Compiler Explorer's `dxc_trunk`.

## The DXIL crash (@llvm-beanz's repro)

```
$ dxc -T ps_6_0 repro.hlsl
Internal compiler error: LLVM Assert
```

The underlying assert is `llvm::StoreInst::AssertOK`, `"Ptr must be a pointer to Val type!"`,
reached from `CodeGenFunction::EmitHLSLVectorElementExpr` — the construct-cast
`float(obj._pad)` leaves an array-typed lvalue where CodeGen expects a scalar, and the
resulting store mismatches types. Release builds don't hit that assert (compiled out) but hit
the same defect one step later via the release-path `llvm::cast<X>()` check:

```
error: llvm::cast<X>() argument of incompatible type!
```

Every stable release from v1.4.1907 (2019-07) through v1.9.2607 — 20 releases — fails this
input, either with one of the two asserts above or — uniquely at v1.5.2010 — with a
self-detected `error: Invalid record` when DXC tries to re-read the module it just emitted.

Link: https://godbolt.org/z/W9Kr6fvPa (`dxc_trunk` crashes on the same defect; `dxc_1_6_2112`
cannot compile the original `ps_6_7` variant used in that CE case).

## The missing diagnostic

The SPIR-V path still emits no warning or error for this construct — codegen silently reads
element 0, matching FXC. That's not itself a bug (per the earlier discussion in this thread),
but it is worth noting DXC *does* check construct-cast element counts in general: changing the
array to two elements produces `error: too many elements in vector initialization (expected 1
element, have 2)`. A single-element array is specifically treated as compatible with a scalar
destination with no diagnostic — the same unchecked case that reaches the crashing DXIL path.

## Suggested labels

No changes — `bug`, `crash`, `dxil` and `diagnostic` already describe this precisely.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5633](https://github.com/microsoft/DirectXShaderCompiler/issues/5633) DXC should warn on statically checkable out-of-bounds

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5633](https://github.com/microsoft/DirectXShaderCompiler/issues/5633).

Still reproduces on `main` (local Debug build, commit `89e2f98e2`) and on every stable
release back to v1.5.2010 (2020-10-22, before v1.4.1907 SPIR-V codegen didn't exist yet) --
this has never diagnosed the reported access.

`dxc -T ps_6_0 -E main -spirv` on the exact repro compiles to completion, exit 0, empty
stderr, and bakes the literal straight into the access chain:
```
%23 = OpAccessChain %_ptr_Uniform_uint %lineStyles %int_0 %uint_45 %int_1 %int_2000
```
against `%_arr_uint_uint_1` (a one-element array). Plain DXIL codegen (no `-spirv`) folds
the same literal into a constant byte offset with no diagnostic either. Verified the same
way on Compiler Explorer against `dxc_1_6_2112`, `dxc_trunk`, and `hlsl_clang_trunk` (the
Clang-based successor front end): https://godbolt.org/z/KG9b5j1f8 -- none of the three warn.

Worth noting: DXC already has a diagnostic for exactly this
(`err_hlsl_array_element_index_out_of_bounds`, "array index N is out of bounds",
exercised by `tools/clang/test/SemaHLSL/array-index-out-of-bounds.hlsl`) -- it's just not
reaching this shape. Reading `Sema::CheckArrayAccess` in
`tools/clang/lib/Sema/SemaChecking.cpp` turned up two things that both apply here:

1. The full-expression entry point only looks through parens/implicit casts, `*`/`&`, and
   `?:` before checking for an array subscript; anything else wrapping the subscript
   (including a swizzle like `.xxxx`) silently exits without checking.
2. A size-1 array that's a struct field is deliberately exempted, to avoid warning on the
   classic C89 flexible-array-member idiom. `_pad` is declared `uint _pad[1]`, which
   matches that exemption even though it's being used here as plain (if oversized) padding,
   not a flexible array.

Either one alone would already hide this; the repro combines both (a struct-member array
of size 1, indexed and then swizzled), so it's fully silent rather than partially caught.

Suggest keeping `bug` + `enhancement` + `diagnostic` as-is, and treating this as narrowing
the existing check's two exemptions rather than adding a new one from scratch.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5668](https://github.com/microsoft/DirectXShaderCompiler/issues/5668) DispatchMesh fails when given an emtpy struct

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5668](https://github.com/microsoft/DirectXShaderCompiler/issues/5668).

Still reproduces on `main` (public commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df)),
with the identical diagnostic as reported:

```
repro.hlsl:7:5: error: For amplification shader with entry 'taskMain', payload size 4 is greater than declared size of 0 bytes.
```

Confirmed on the current stable release and Compiler Explorer trunk:
https://godbolt.org/z/rqTqed5s8

Bisecting all stable releases back to the oldest one that supports `as_6_6`
(v1.6.2104, 2021-04-20) shows this has never worked; it is not a regression.

**Root cause, from source:** `ValidateAsIntrinsics` in
`lib/DxilValidation/DxilValidation.cpp` measures the payload *pointer's*
`DataLayout` alloc size (a constant 4 bytes, from DXIL's 32-bit pointer
layout) instead of dereferencing to the pointee struct's size, then compares
that constant against the correctly-computed declared size. The declared
size for `struct S{}` is genuinely 0 — `-Vd` still emits a `0`-byte
payload-size record in DXIL metadata — so the check is really testing "declared size < 4", not
"declared size < actual size". That is invisible for every ordinary payload
(real size ≥ 4 bytes), and only fires for a zero-byte one.

So this is a validator bug independent of whether an empty/absent
amplification-shader payload should be legal HLSL (a language-policy
question this doesn't resolve): the validator's own bookkeeping disagrees with itself about the
size of the same value.

This looks like the same defect as #5269 (filed three months earlier),
which independently reaches the same source-level conclusion.

Suggested label: `validation` (in addition to `bug`) — the defect is
entirely inside the DXIL validator's own size comparison, not in front-end
acceptance or in code generation for the payload itself.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
````

### Draft — [#5674](https://github.com/microsoft/DirectXShaderCompiler/issues/5674) Crash in syntax check when using 'matrix' keyword in an operation

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5674](https://github.com/microsoft/DirectXShaderCompiler/issues/5674).

Still reproduces on `main` (89e2f98e2, Debug build):

```
Internal compiler error: access violation. Attempted to read from address 0x0000000000000038
```

Compiler Explorer: https://godbolt.org/z/bsEPd3eaY — `dxc_1_6_2112` (oldest available there)
rejects the declaration cleanly; `dxc_trunk` crashes (`SIGSEGV` on Linux, same defect as the
Windows access violation).

**History:** bisected across the 20 stable releases back to v1.4.1907 (2019-07). This did
*not* always crash. Through v1.6.2112 (2021-12-08), `float2x2 matrix;` was rejected outright
at parse time:

```
error: template specialization requires 'template<>'
error: cannot refer to class template 'matrix' without a template argument list
```

Starting at v1.7.2207 (2022-07-18) that declaration is accepted, and using `matrix` afterward
crashes instead. The transition lines up with `a7fa058dd` ("Rework name lookup", #4332,
2022-04-12), whose own description says it made bare `matrix` (no `<>`) valid in HLSL — that
appears to have also made it possible to shadow `matrix` as a variable name, which the
overload-resolution path for `*` doesn't handle: the crash is in `ArgumentDependentLookup` /
`FindAssociatedClassesAndNamespaces`, dereferencing an invalid `ValueDecl` for the `matrix`
operand. This attribution is strong but not proven (the exact commit wasn't built and tested
in isolation).

Suggest adding `matrix-bug` alongside the existing `bug`/`crash`/`incorrect-code` labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5681](https://github.com/microsoft/DirectXShaderCompiler/issues/5681) Segmentation fault/ICE when attempting a particular (invalid) code pattern

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5681](https://github.com/microsoft/DirectXShaderCompiler/issues/5681).

Still an invalid program, but no longer reproduces on `main` (89e2f98e2, `1.9.0.5465`):
`InterlockedMax(b.Load<T>(0).value, 1, original)` now compiles to a clean diagnostic instead of
crashing.

```
error: cannot map resource to handle.
repro.hlsl:9:3: error: Atomic operation targets must be groupshared, Node Record or UAV.
  InterlockedMax(b.Load<T>(0).value, 1, original);
  ^
```

A release history search (`v1.4.1907` .. `v1.9.2607`) confirms this was an access violation on
every release from `v1.6.2104` (the first release to support `-T cs_6_6` /
`ResourceDescriptorHeap`) through `v1.8.2502`, then fixed in `v1.8.2505`:

```
Internal compiler error: access violation. Attempted to read from address 0x0000000000000008
```

[Compiler Explorer](https://godbolt.org/z/vfcsj3ThG) corroborates both ends independently:
CE's oldest DXC (`1.6.2112`) still crashes (`SIGSEGV`), current `dxc_trunk` emits the same
clean diagnostic as the local build above.

Suggested labels: no change — `bug`, `crash`, `diagnostic` and `incorrect-code` all still
describe the report accurately.

Suggested action: close as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5682](https://github.com/microsoft/DirectXShaderCompiler/issues/5682) Install error

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5682](https://github.com/microsoft/DirectXShaderCompiler/issues/5682).

Still reproduces on `main` (commit `89e2f98e2`) — confirmed by reading the CMake rule graph
rather than by re-running the failing install, since this is a CMake configuration defect, not
a `dxc` compiler behavior.

**Root cause:** `tools/llvm-as/CMakeLists.txt` excludes `llvm-as` from the default build
(`EXCLUDE_FROM_ALL`) whenever `HLSL_OPTIONAL_PROJS_IN_DEFAULT` is `OFF` — its default. But
`add_llvm_tool` (`cmake/modules/AddLLVM.cmake`) already registered an unconditional
`install(TARGETS llvm-as ...)` rule before that exclusion is applied, so `cmake_install.cmake`
still tries to copy `llvm-as.exe` for the plain `install` target even though it was never built.
This is unchanged in the tree from before this issue was filed through the current commit.

This is exactly what the duplicate report, #5867, found independently ("`llvm-as` ... which was
never built"), and `@llvm-beanz` closed it as a duplicate of this issue with the same
conclusion.

**Workaround that already works today:** the `install-distribution` target
(`CMakeLists.txt`, added in #5154, predates this issue) installs only the `dxc`, `dxcompiler`
and `dxc-headers` components via per-component `install-<component>` custom targets, so it never
reaches `llvm-as`'s install rule at all. It's what DXC's own Linux CI uses
(`gcp-pipelines/x86_64-linux-clang.yml`), and matches `@bjconlan`'s suggestion above. It isn't
documented anywhere outside `CMakeLists.txt` and that CI file, which is presumably why
`@namandixit`'s question above went unanswered.

Given `@pow2clk`'s and `@damyanp`'s comments that the plain `install` target isn't expected to
work and a PR would be welcome: `build`, `up-for-grabs` looks right for labels; recommend
keeping open rather than closing, and consider pointing users at `install-distribution` from
the docs in the meantime.

---
<sub>Triaged with AI assistance. This finding was verified by reading the CMake source (no
build was run); please flag anything that looks wrong.</sub>
````

### Draft — [#5686](https://github.com/microsoft/DirectXShaderCompiler/issues/5686) Validation fails when linking to amplification shader target

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5686](https://github.com/microsoft/DirectXShaderCompiler/issues/5686).

Still reproduces on `main` (89e2f98e2). Compiling `as.hlsl` directly to `-T as_6_6` validates
cleanly; compiling it to `-T lib_6_x` and then `dxc -T as_6_6 -link as.lib` fails with the same
error as reported:

```
Function: main: error: For amplification shader with entry 'main', payload size 8 is greater than declared size of 4 bytes.
```

A full linear scan of all 18 probeable releases from `-link`'s first shipped release
(v1.6.2106, 2021-07) through the current v1.9.2607 reproduces it on every one — there is no
release where it worked, so the bug predates the report by over two years rather than the
other way around. (Three older releases reject `-link` outright as an unknown argument,
confirmed genuinely absent via `--help` rather than a spelling issue, and are excluded from
that range.)

Root cause looks like two separate bugs compounding:

1. `ValidateAsIntrinsics` in `DxilValidation.cpp` computes the amplification shader's payload
   size from `DispatchMesh`'s payload **pointer** type, not the pointee struct — it's missing
   the `->getPointerElementType()` step that the neighbouring mesh-shader check (three lines
   above) does have. So the "declared vs. actual" comparison is really "declared vs. pointer
   size", regardless of the real payload struct.
2. `DxilLinkJob::Link` in `DxilLinker.cpp` builds the linked module and copies the target
   triple, but never calls `setDataLayout` — it never has, in the entire history of that file.
   The linked module falls back to LLVM's default data layout, whose pointer size is 8 bytes,
   versus DXIL's own layout string, which declares 4-byte pointers.

Put together: bug 1 makes the check effectively test "declared payload size >= pointer size"
rather than the real payload size, which is very rarely false for a direct compile (4-byte
DXIL pointer) but always false for anything under 8 bytes once linked (8-byte default
pointer) — independent of whether the payload is actually correctly sized. A payload of 8
bytes or larger would pass either way, correctly sized or not, because the check never
inspects the real struct.

Labels (`bug`, `shader-linking`, `validation`) already look right; no changes suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5703](https://github.com/microsoft/DirectXShaderCompiler/issues/5703) RDAT part is missing when linking a compute shader

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5703](https://github.com/microsoft/DirectXShaderCompiler/issues/5703).

Reproduced on current `main` (`89e2f98e2`) and the reported build
(`v1.7.2308`), so this hasn't changed since filing.

The behavior is by design, not a bug: `RDAT` (`DXC_PART_REFLECTION_DATA`)
is written only for library modules
(`lib/DxilContainer/DxilContainerAssembler.cpp`, keyed on
`ShaderModel::IsLib()`). A finalized, non-library container -- which is
what `IDxcLinker::Link(entry, "cs_6_3", ...)` produces -- gets `PSV0`
instead, and never `RDAT` (just like a shader compiled *directly* to
`cs_6_3`). Confirmed both ways:

- library compile: `SFI0, VERS, RDAT(232), STAT, HASH, DXIL`
- linked to `cs_6_3`: `SFI0, ISG1, OSG1, PSV0(132), STAT, ILDN, HASH, DXIL`
- direct compile to `cs_6_3` (no linker involved at all): identical to
  the linked case (no `RDAT`).

The resource-binding information isn't lost -- `dxa
-dumpreflection` (which drives `ID3D12ShaderReflection`, not
`ID3D12LibraryReflection`) on the linked container correctly reports both
`texResource` (`t900`) and `rwTexResource` (`u0`, space2400). `RDAT`
specifically feeds `ID3D12LibraryReflection`, which doesn't apply once a
shader has been finalized to a concrete profile; `ID3D12ShaderReflection`
is the interface to use on a linked/compiled container, and it works.

Suggest dropping `bug` -- `reflection` and `shader-linking` still fit. A
short doc note (or a remark on `IDxcLinker::Link`) stating that a
linked/finalized container never carries `RDAT`, and that
`ID3D12ShaderReflection` is the correct reflection interface post-link,
would clarify this.

(Aside: the literal repro no longer links on current `main` -- `dxl`
reports "Cannot find definition of function main" -- because
`[numthreads]` alone doesn't tag an entry point without an accompanying
`[shader("compute")]`; it did link at v1.7.2308. Adding
`[shader("compute")]` restores it and doesn't change the RDAT finding
above. Flagging this only so it isn't confused with the RDAT question if
this gets revisited.)

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5704](https://github.com/microsoft/DirectXShaderCompiler/issues/5704) Linker doesn't strip resource names when using -Qstrip\_reflect

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5704](https://github.com/microsoft/DirectXShaderCompiler/issues/5704).

Re-tested this against the reporter's own v1.7.2308 and against current
`main` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df).

**The reported defect reproduced exactly as filed on v1.7.2308**: compiling
the repro to `lib_6_3` with `-Qstrip_reflect`, linking to `cs_6_3` with
`-Qstrip_reflect`, and disassembling shows both `texResource` and
`rwTexResource` still present.

**It is fixed as of v1.8.2403** (no stable release exists between v1.7.2308
and v1.8.2403 to narrow the window further). To measure this, the repro had
to be adapted: the reported function has no `[shader("compute")]` attribute,
and current `dxc` now gives an attribute-less, `numthreads`-only function in
a `lib_6_3` compile internal linkage, so it is dead-code-eliminated before it
can even be linked (`error: Cannot find definition of function main`). That
appears to be a separate, newer change from the reported bug, worth its own
issue if it isn't already tracked — it means today's `dxc` can't even run
your exact repro, let alone show the original symptom. Adding
`[shader("compute")]`, which the current front end requires regardless of
this issue, restores a working pipeline, and in that form `-Qstrip_reflect`
now correctly produces an empty resource name and an `undef` global in the
linked disassembly. A direct (non-library) compile strips cleanly on both
old and current builds, confirming the difference is specific to the
lib→link path this issue is about.

Suggested labels: no change — `bug`, `reflection`, `shader-linking` still
describe this correctly.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5721](https://github.com/microsoft/DirectXShaderCompiler/issues/5721) DXC linker API doesn't include DXC\_OUT\_PDB in the result

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5721](https://github.com/microsoft/DirectXShaderCompiler/issues/5721).

Reproduced on current `main` (`89e2f98e2`).

Confirmed with a small COM harness that drives `IDxcLinker::Link` and
`IDxcResult` directly (this can't be seen from a `dxc`/`dxl` command
line -- the CLI's link path never asks for `DXC_OUT_PDB` either):

- `Link("main", "cs_6_3", {-Zi,-Qstrip_debug})` succeeds.
- On the linked `IDxcResult`: `HasOutput(DXC_OUT_PDB)` is `FALSE`, and
  `GetOutput(DXC_OUT_PDB, ...)` returns `E_INVALIDARG` -- exactly the
  reported behavior.
- Self-test on the same result object: `GetOutput(DXC_OUT_OBJECT, ...)`
  succeeds, so the plumbing isn't broken -- `DXC_OUT_PDB` specifically was
  never populated.
- Control: compiling the identical source directly to `cs_6_3` with the
  identical `-Zi -Qstrip_debug` flags (no linker) *does* produce a PDB --
  isolates the gap to the linker path.

Root cause: `tools/clang/tools/dxcompiler/dxclinker.cpp`'s `Link()`
builds `DXC_OUT_OBJECT`/`DXC_OUT_ROOT_SIGNATURE`/`DXC_OUT_SHADER_HASH`/
`DXC_OUT_REFLECTION` outputs (added by
[#5678](https://github.com/microsoft/DirectXShaderCompiler/pull/5678))
immediately followed by a bare `// TODO: DFCC_ShaderDebugName` comment --
`DXC_OUT_PDB` was never wired up alongside those. `IDxcResult::GetOutput`
returns `E_INVALIDARG` for any output slot that was never
`SetOutputObject`'d, which is exactly what happens here.

There's already an open PR for this:
[#6834](https://github.com/microsoft/DirectXShaderCompiler/pull/6834)
("Add PDB output to linker") adds the missing `SetOutputObject` call and
says it fixes this issue; it just hasn't merged yet. Suggest keeping this
open until that lands rather than treating it as needing fresh
repro/triage.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5723](https://github.com/microsoft/DirectXShaderCompiler/issues/5723) Revise extra metadata error reporting in DxilMetadataHelper

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5723](https://github.com/microsoft/DirectXShaderCompiler/issues/5723).

Checked against `main` @ `13730886e` (Debug build, self-reports an orphaned fork-local merge
commit whose tree is identical to that upstream commit outside this triage tooling).

This is a design proposal, not a bug repro, so there's nothing to compile — the check here is
source inspection instead:

- The implementation this issue describes is still exactly what's in
  `lib/DXIL/DxilMetadataHelper.cpp` today: an unrecognized extended-metadata tag still trips
  `DXASSERT(false, "Unknown ...")` immediately followed by a bare `m_bExtraMetadata = true;`,
  with no captured location/context, at every call site handling extended lists (SRV/UAV/
  CBuffer/sampler properties, signature elements, subobjects, payload qualifiers, node
  records, shader-specific properties).
- No `MetaErrorContext`/`PushErrorContext` or equivalent context-capture mechanism exists
  anywhere in the tree (`git grep`, whole repo, zero hits).
- The linked implementation branch,
  [`tex3d/DirectXShaderCompiler:metadata-error-reporting`](https://github.com/tex3d/DirectXShaderCompiler/tree/metadata-error-reporting),
  is unchanged since a single commit at `2023-09-14T23:12:46Z` (13 minutes before this issue
  was filed) and has never been merged or cross-referenced by any PR.

So the report is still entirely accurate — nothing here needs a title/body correction. What's
missing is a decision on next steps rather than more measurement: is `metadata-error-reporting`
still the intended design and worth finishing (it's described as "code-complete, barring any
desired design changes, but tests still need to be written")? Suggesting `needs-human-judgement`
rather than closing or leaving as a plain backlog item, since only a maintainer can say whether
to revive that branch, ask for it to be updated, or deprioritize the idea.

---
<sub>Triaged with AI assistance. Findings were produced by source inspection of the tree at the
cited commit and read-only GitHub API queries; please flag anything that looks wrong.</sub>
````

### Draft — [#5736](https://github.com/microsoft/DirectXShaderCompiler/issues/5736) Internal compiler error when attempting to link a non-library input

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5736](https://github.com/microsoft/DirectXShaderCompiler/issues/5736).

Still reproduces on current `main` (commit `89e2f98e2`):

```
$ dxc -T cs_6_3 -Fo test.bin test.hlsl
$ dxc -link -T cs_6_3 -Fo test2.bin test.bin
Internal compiler error: access violation. Attempted to read from address 0x0000000000000000
```

Identical crash text and address to the original 1.7.2207.3 report. Checked
every stable release from v1.6.2106 (2021-07, when `-link` was introduced)
through v1.9.2607 (2026-07): all of them crash the same way. Releases before
v1.6.2106 don't have `-link` at all (`Unknown argument: '-link'`), so this has
reproduced for as long as the option has existed.

@elasota's root-cause theory above checks out as far as this triage went:
linking the same shader compiled as a **library** target instead (so it uses
`createHandleForLib` and carries the resource global variables `AddGlobals`
expects) does not crash:

```
$ dxc -T lib_6_3 -Fo control-lib.bin control-lib.hlsl
$ dxc -link -T cs_6_3 -Fo control-lib2.bin control-lib.bin
[exit] 0
```

So the crash is specific to feeding a non-library (`createHandle`-based)
module into the linker, consistent with the theory that `DxilLinkJob::AddGlobals`
never learns about that module's resources and a later out-of-bounds lookup
walks off the end of the (for this module, empty) resource list.

No fix appears to have landed for this since the 2024-07-30 comment.

Current labels (`bug`, `crash`, `shader-linking`, `incorrect-code`) already
describe this well; no change suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5737](https://github.com/microsoft/DirectXShaderCompiler/issues/5737) Link fails when using -Fd with -Qstrip\_debug

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5737](https://github.com/microsoft/DirectXShaderCompiler/issues/5737).

Still reproduces on `main` (commit `13730886e`).

```
dxc.exe -T lib_6_3 -Zi -Qstrip_reflect -Qembed_debug -Fd testc.pdb -Fo test.lib test.hlsl
dxc.exe -link -T lib_6_3 -Zi -Qstrip_reflect -Qstrip_debug -Fd test.pdb -Fo test.bin test.lib
```
```
dxc failed : DXIL container does not contain the given part.
```

The failure is actually broader than `-Fd` + `-Qstrip_debug` combined:
`-link -Qstrip_debug` alone, with no `-Fd` at all, fails identically. So the
defect is in linking with `-Qstrip_debug`, not specifically in the
interaction with `-Fd`.

[PR #6833](https://github.com/microsoft/DirectXShaderCompiler/pull/6833)
("Fix -link -Qstrip_debug failing") already targets this and says it fixes
this issue, but it is still open and unmerged.

Bisected across every release with the built-in `-link` mode
(v1.6.2106, 2021-07-01, onward through v1.9.2607): always fails, so this
was never fixed and always affects that whole range, including the
reporter's v1.7.2207.3.

Labels (`bug`, `shader-linking`) look right as-is.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5739](https://github.com/microsoft/DirectXShaderCompiler/issues/5739) DXC linker debug output isn't a valid PDB (and doesn't work with PIX)

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5739](https://github.com/microsoft/DirectXShaderCompiler/issues/5739).

Still reproduces on `main` (commit 13730886e, built locally at
89e2f98e29c289ae8ad9e00dd310104fea9fd7df, which is source-identical to that public
commit).

Using the repro from the issue: after `dxc -T lib_6_3 -Zi -Qembed_debug -Fd testc.pdb ...`
then `dxc -link ... -Zi -Fd test.pdb ...`, `dxc -dumpbin` shows the difference directly:

```
$ dxc -dumpbin testc.pdb        (compile step's own -Fd output)
; shader debug name: testc.pdb
; shader hash: eba41e9d71c52c629a3e63dca25af48a
;
; Buffer Definitions:
...

$ dxc -dumpbin test.pdb         (link step's -Fd output)
;
; Buffer Definitions:
...
```

`testc.pdb` starts with the standard MSF7 PDB magic
(`Microsoft C/C++ MSF 7.00\r\n\x1aDS...`); `test.pdb` starts with `DXIL` followed by the
raw LLVM bitcode magic (`BC\xc0\xde`) — it's the ILDB part's bytes with no PDB container
around them, so `-dumpbin` disassembles it but can't print a debug name.

Checked history across every stable release that supports `-link` at all (v1.6.2106,
2021-07-01, onward — `-link` itself didn't exist before that): every one reproduces the
same symptom, so this has never worked since the linker CLI shipped, and the 2023-09-18
report sits in the middle of that range, not near either end.

Two open PRs already target this: #6833 ("Fix `-link -Qstrip_debug` failing") and #6834
("Add PDB output to linker"). Neither is merged yet.

Suggested labels: keep `bug`, `shader-linking`, `debug info` — no changes needed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5744](https://github.com/microsoft/DirectXShaderCompiler/issues/5744) Intrinsics ddx\_fine/ddy\_fine should not be allowed to sink into flow control

````markdown
> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5744](https://github.com/microsoft/DirectXShaderCompiler/issues/5744).

This is fixed on `main` as of commit `28d9915fa0` (PR
[#8707](https://github.com/microsoft/DirectXShaderCompiler/pull/8707),
merged 2026-07-31), but the fix was recorded against
[#8001](https://github.com/microsoft/DirectXShaderCompiler/issues/8001),
a later-filed issue describing the identical defect -- so this issue never
got closed. No shipped release contains the fix yet: the newest stable
release, v1.9.2607, was built 2026-07-29, two days before the fixing commit.

The derivative DXIL ops (`DerivCoarseX/Y`, `DerivFineX/Y`) were not marked
`convergent`, so LLVM's optimizer could legally sink a call to one of them
into a conditional block when its result was only used there -- exactly the
symptom this issue describes. #8707's own commit message says: "Previously,
the various derivative operations were not marked as convergent, which
allows their results to be sunk into conditional branches. This change
fixes that **and removes the workaround for this issue from the execution
tests**" -- that workaround-removal is the same `-opt-disable sink` change
this issue's own repro steps ask for.

Verified with a static repro (no GPU needed -- this is visible directly in
the disassembled DXIL): a compute shader computes `ddx(value)` unconditionally
and only stores it inside `if (WaveGetLaneIndex() == 3)`. Before the fix, the
derivative call itself moves into that conditional block:

```
%DerivCoarseX = call float @dx.op.unary.f32(i32 83, float %2)  ; -- inside the `if`
```

On `main` today, it stays where the source put it, unconditional:

```
%5 = call float @dx.op.unary.f32(i32 83, float %4)  ; DerivCoarseX(value) -- before the branch
```

Bisecting the stable release history (v1.4.1907 and v1.5.2010 can't run
this repro at all -- SM 6.6 postdates them, so they're excluded, not
"fixed"), every release from v1.6.2104 through v1.9.2607 reproduces the sink.
Compiler Explorer corroborates: [the linked
case](https://godbolt.org/z/vrMMYWr31) still shows the sink on CE's oldest
DXC (`dxc_1_6_2112`), and no longer shows it on CE's rolling `dxc_trunk`
build.

Current labels (`bug`, `correctness`) still fit. Suggest closing this as a
duplicate of #8001, which already carries the fix and its own closure.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5748](https://github.com/microsoft/DirectXShaderCompiler/issues/5748) Groupshared memory used through patch constant function allowed in hull shaders 

````markdown
> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5748](https://github.com/microsoft/DirectXShaderCompiler/issues/5748).

This no longer reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).
Compiling the repro as a library target (`-T lib_6_3`, and separately re-checked at the
originally-filed `-T lib_6_5`) now correctly fails validation:

```
error: validation errors
<source>:47:16: error: Thread Group Shared Memory not supported from non-compute entry points.
note: at '%1 = load float, float addrspace(3)* @"...gs.0", align 4' in block '#0' of
function '?HSPatch@@YA?AUPCStruct@@...'.
```

The diagnostic names the patch-constant function (`HSPatch`) directly, not just the
`[shader("hull")]` entry point -- confirming the validator's library-target path now visits
patch-constant functions.

A release-binary bisection across the full stable-release catalog puts the fix at
**v1.9.2607**: every stable release from v1.4.1907 through v1.9.2602.24 still reproduces the
bug (library target validates cleanly despite the groupshared read), and v1.9.2607 onward does
not.

Comparison on Compiler Explorer (CE's oldest DXC vs. current trunk):
https://godbolt.org/z/daqY8a3x8

PR #5749 (opened by this issue's reporter, same day, `Fixes #5748`) proposed a fix but was
never merged -- it was closed unmerged by an inactivity sweep after two years. The measured
release transition indicates this issue was fixed instead as an incidental effect of PR #8140
("Add GroupSharedLimit attribute support for Mesh, Amp and Node shaders"), which changed the
same library-target validation loop to also visit patch-constant functions and added a
regression test. That PR's merge date is earlier than the release that first ships the fix,
so the exact commit-to-release mapping isn't fully pinned down, but the release-binary
transition itself (v1.9.2602.24 -> v1.9.2607) is a direct measurement, not an inference.

Suggest closing as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5768](https://github.com/microsoft/DirectXShaderCompiler/issues/5768) Declare SV\_VertexID as float only get validation error

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5768](https://github.com/microsoft/DirectXShaderCompiler/issues/5768).

Still reproduces on `main` (commit `89e2f98e2`, `main-debug`). Compiling

```hlsl
float4 main(float V : SV_VertexID) : SV_Position {
   return V;
}
```

with `-T vs_6_0` gives:

```
error: validation errors

error: SV_VertexID must be uint.
Validation failed.
```

The shader still passes the front end and is only rejected once DXIL is emitted and
validated, exactly as reported.

Confirmed across every probeable stable release from v1.4.1907 through v1.9.2607 (linear
scan, no transitions) and on Compiler Explorer's oldest (`dxc_1_6_2112`) and rolling
`dxc_trunk` builds alike:
https://godbolt.org/z/PWdbvjGP3

This isn't unaddressed: PR #3043 added exactly this class of check (including a
`SV_VertexID`-specific test) and merged in Feb 2021, but was reverted five days later "due to
regressions," with a note to re-merge once fixed. That never happened — both the merge and
the revert land entirely between two stable releases (v1.5.2010 and v1.6.2104), so no
released `dxc` ever shipped the check, and no follow-up has landed since.

Current labels (`bug`, `tech-debt`, `diagnostic`) already fit well. Given the type-system
angle and the fact that today's rejection point is the validator, consider adding
`type-system` and `validation`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5790](https://github.com/microsoft/DirectXShaderCompiler/issues/5790) [Github] Enable "Require conversation resolution before merging" ?

````markdown
> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5790](https://github.com/microsoft/DirectXShaderCompiler/issues/5790).

This is a repository-settings question, so I checked the current GitHub configuration for
`main` rather than running the compiler.

As of today, "Require conversation resolution before merging" is **not** enabled for `main`:

- Classic branch protection: `"required_conversation_resolution": {"enabled": false}`
- The `microsoft-production-ruleset` (org-sourced, applies to `~DEFAULT_BRANCH`, created
  2025-05-07) also has its equivalent rule off: `"required_review_thread_resolution": false`

So the 2023-10-25 note that this "has been done for all branches" no longer matches the live
setting, which is consistent with @Keenuts' 2025-04-23 report that an approval-with-a-comment
still let auto-merge submit PR #7369. GitHub does not expose branch-protection change
history, so I can't tell whether the classic setting was later turned off, or whether it was
superseded when the `microsoft-production-ruleset` was introduced in May 2025 without this
rule enabled.

Since this is an org/repo-admin setting rather than a compiler behavior, only a maintainer
with admin access can say whether that was intentional or should be re-enabled.

---
<sub>Triaged with AI assistance. The GitHub API results above were fetched read-only just now;
please flag anything that looks wrong.</sub>
````

### Draft — [#5801](https://github.com/microsoft/DirectXShaderCompiler/issues/5801) Sample immediate offset range is not diagnosed or validated in SM 6.7

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5801](https://github.com/microsoft/DirectXShaderCompiler/issues/5801).

Still reproduces on `main` (commit `89e2f98e2`, `1.9.0.5465`). The repro shader compiles
cleanly at `-T ps_6_7` with the offset `int2(12, -14)` embedded verbatim in the DXIL `Sample`
op, no diagnostic and no validation error:

```
%7 = call %dx.types.ResRet.f32 @dx.op.sample.f32(..., i32 12, i32 -14, ...)
```

The same source at `-T ps_6_6` still correctly rejects it:
`error: Offsets to texture access operations must be between -8 and 7.`

Bisecting the stable release history: every release that can target `ps_6_7` reproduces
(`v1.7.2207` through `v1.9.2607`, and current `dxc_trunk` on Compiler Explorer:
https://godbolt.org/z/WT19a1jbM). No earlier stable release can even select the profile, so this
has never worked rather than having regressed — it dates to SM 6.7's introduction.

@python3kgae's diagnosis is confirmed by reading the source: both guards that key off
`IsSM67Plus()` bypass their range check unconditionally, rather than only for the non-constant
("programmable") offsets SM 6.7 was meant to permit:

- `lib/HLSL/DxilLegalizeSampleOffsetPass.cpp:88-90` skips `FinalCheck` (the front-end/legalizer
  diagnostic) entirely once `IsSM67Plus()`.
- `lib/DxilValidation/DxilValidation.cpp:369-372` (`ValidateResourceOffset`'s `ValidateOffset`)
  returns before checking the `ConstantInt` case once `IsSM67Plus()`, even though the comment
  right above it ("6.7 Advanced Textures allow programmable offsets") only motivates skipping
  the non-constant branch below it.

Suggesting `sm6.7` in addition to the current labels, since both root-cause sites and the first
reproducing release are keyed on that shader model specifically.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5804](https://github.com/microsoft/DirectXShaderCompiler/issues/5804) Fix UBSAN alignment failures

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5804](https://github.com/microsoft/DirectXShaderCompiler/issues/5804).

Checked against `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`): the suppression
this issue is about is still in place.

`cmake/modules/HandleLLVMOptions.cmake` still excludes `alignment` from both UBSAN
configurations:

```
append("-fsanitize=undefined -fno-sanitize=vptr,function,alignment -fno-sanitize-recover=all" ...)
append("-fsanitize=address,undefined -fno-sanitize=vptr,function,alignment -fno-sanitize-recover=all" ...)
```

That's exactly the pair added by #5803 and its follow-up #6431 ("Disable ubsan alignment
errors properly", which covered the `Address;Undefined` config #5803 missed).
`DxilPipelineStateValidation::CheckedReaderWriter` carries no narrower in-code suppression
either, so the blanket CMake exclusion described here is still the only thing standing between
this build and the alignment failures.

No shader repro applies — this is a build-configuration issue, not a compile-time one — so
"reproduces" here means the exclusion is still present, which it is.

Suggested labels: add `sanitizer` (fault detected by sanitizer run) and `build` (build/setup);
current `bug` and `tech-debt` are also accurate.

---
<sub>Triaged with AI assistance. The source excerpt above was read directly from the
repository at the cited commit; please flag anything that looks wrong.</sub>
````

### Draft — [#5807](https://github.com/microsoft/DirectXShaderCompiler/issues/5807) Error in implicit conversions when enums are involved

````markdown
> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5807](https://github.com/microsoft/DirectXShaderCompiler/issues/5807).

Still reproduces on `main` (89e2f98e2, current at time of triage):

```
repro.hlsl:7:22: error: cannot convert from 'unsigned int' to 'E'
    uint e = E::A << 1u;
                     ^
```

Confirmed across the full stable release history (v1.4.1907 through v1.9.2607) and on
Compiler Explorer's `dxc_1_6_2112` and `dxc_trunk`: https://godbolt.org/z/dE4KrbPjY

@llvm-beanz's diagnosis holds up against the source: `AR_BASIC_ENUM` (unscoped enum) is
already flagged numeric/integer, and `ConvertComponent` already has an explicit `enum ->
int/float` path, so the general implicit-conversion machinery isn't missing this case -- the
defect is narrower, in how the built-in shift-operator overload set gets resolved for an
`E`/`uint` operand pair. `E::A | 1u` compiles fine on the same build, which matches that.

On the same link, the new Clang-based HLSL front end (`hlsl_clang_trunk`) already compiles this
shader cleanly and lowers it correctly.

Labels (`bug`, `hlsl-next`) already match this finding; no changes proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5823](https://github.com/microsoft/DirectXShaderCompiler/issues/5823) [SPIR-V] SIGSEGV when defining a partial specialization array static member

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5823](https://github.com/microsoft/DirectXShaderCompiler/issues/5823).

Tested against `main` (`1.9.0.5465`, `89e2f98e2`).

The original SIGSEGV is fixed — since `v1.7.2308` (2023-08-14), this exact repro no longer
crashes. It now exits `0x80004005` with a diagnosed error instead:

```
repro.hlsl:12:1: error: casting to type 'void' unimplemented
```

That fix is **PR #8079**, which stops the SPIR-V backend from emitting a variable for the
un-instantiated template-declaration `VarDecl` (detected via
`CXXRecordDecl::getDescribedClassTemplate()`). That guard only matches a **primary**
(non-specialized) template's declaration context — it does not match a
`ClassTemplatePartialSpecializationDecl`, so the original repro's partial-specialization
member (`GaussLegendreValues<2, float_t>::wi`) still falls through to the same
"casting to type 'void' unimplemented" codepath as before, just without crashing. Bisecting
the crash-only signature gives `fixed-in v1.7.2308`; bisecting "crash or this diagnosed
text" gives `always-repro'd` across every probeable release `v1.7.2207`..`v1.9.2607` —
this input has never successfully compiled.

That also explains the December retitle and the two February complaints, which are a second,
related but distinct bug. Testing the full matrix on `main-debug`:

| Template kind | OOL spelling | Result |
|---|---|---|
| Primary template or full/explicit specialization | illegal duplicated `static` | compiles clean |
| Primary template or full/explicit specialization | correct (single `const`) | `'const' is not a valid modifier for a field` |
| Partial specialization | either spelling | `casting to type 'void' unimplemented` |
| Non-template struct | illegal duplicated `static` | compiles clean, **no diagnostic at all** |

So for a full/explicit specialization or a plain (non-specialized) template, DXC's parser
keys off the presence of the (illegal) `static` token to recognize an OOL specialization
definition; drop it — the standards-correct spelling — and it's misparsed as a new in-class
field and rejected. This matches what `devshgraphicsprogramming` already reported on **#6677**
(2025-12-10, `'const' is not a valid modifier for a field`), where they asked whether to track
it here — the same defect. `#6677`'s narrower ask
(fully generic C++11-style deduced OOL initializers) was correctly closed `NOT_PLANNED` per
`llvm-beanz`'s explanation there (HLSL templates are intentionally C++98-shaped); that part
is a language feature gap, not a bug. But the bogus `'const'` diagnostic reproduces even for
a **full/explicit** specialization, where no deduction is involved at all, so it isn't
covered by that rationale.

And separately, DXC really does silently accept the illegal duplicated `static` — confirmed
on a plain non-template struct with no diagnostic and the constant genuinely folded into
SPIR-V — matching Clang, which rejects the equivalent construct with `'static' can only be
specified inside the class definition`.

Compiler Explorer: **https://godbolt.org/z/dsK39nrKE** (`dxc_1_6_2112`, `dxc_trunk`).
`dxc_trunk` still shows the "casting to void" text for the primary repro (its Release build
lags the local ground truth, which shows the same text for this repro but the newer
`'const'`-field text on corrected-syntax variants — text is not portable across builds, but
"still fails to compile" holds either way).

Suggest keeping `bug`, `spirv`; consider adding `diagnostic` (missing diagnostic for the
illegal `static`, and the bogus `'const'` diagnostic when the syntax is corrected).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5824](https://github.com/microsoft/DirectXShaderCompiler/issues/5824) [Test] Move clang diagnostic tests to verifiertest.cpp

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5824](https://github.com/microsoft/DirectXShaderCompiler/issues/5824).

Still unaddressed on `main` (89e2f98e2). `GSMainMissingAttributeFail` and
`GSOtherMissingAttributeFail` are still registered in
`tools/clang/unittests/HLSL/ValidationTest.cpp`:

```cpp
TEST_F(ValidationTest, GSMainMissingAttributeFail) {
  TestCheck(L"..\\CodeGenHLSL\\attributes-gs-no-inout-main.hlsl");
}

TEST_F(ValidationTest, GSOtherMissingAttributeFail) {
  TestCheck(L"..\\CodeGenHLSL\\attributes-gs-no-inout-other.hlsl");
}
```

and are still absent from `tools/clang/unittests/HLSL/VerifierTest.cpp`.

The premise checks out: both tests call `TestCheck()`, which runs the file's
`// RUN: %dxc ... | FileCheck %s` line — not `CheckValidationMsgs()`, the fixture's other
helper that actually calls `IDxcValidator::Validate`. Compiling both backing files directly
confirms it too: each produces `error: stream-output object must be an inout parameter` and
exits `0x80004005` (E_FAIL, an ordinary diagnosed error) before any DXIL container exists to
validate. So despite living in `ValidationTest`, these two are exercising a clang/Sema
diagnostic, exactly as described.

This isn't something a release-history bisection can answer — no `dxc` invocation's output
depends on which `.cpp` file registers a unit test — so there's no Compiler Explorer link;
the evidence here is source reading plus one confirmatory compile.

One thing worth flagging: the issue's second sentence generalizes to "any other tests inside
validationTest that only test clang diagnostics." This review only checked the two named
tests; it did not audit the rest of `ValidationTest.cpp` for further candidates, so the
broader clause is neither confirmed nor refuted here.

For context: the issue carries a `Dormant` milestone (added 2024-10-23), no assignee, and no
linked PR in its timeline.

Labels (`enhancement`, `test`) still look right; no change suggested.

---
<sub>Triaged with AI assistance. This assessment was produced by reading the current source
directly and confirming the diagnostic's layer with one ground-truth compile; please flag
anything that looks wrong.</sub>
````

### Draft — [#5848](https://github.com/microsoft/DirectXShaderCompiler/issues/5848) DXC possibly emitting spurious [-Wpayload-access-trace] PAQ warnings in SM 6.7

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5848](https://github.com/microsoft/DirectXShaderCompiler/issues/5848).

Tried to reproduce this from the code in the report against current
`main` (`89e2f98e2`) and against the exact build named here, `1.7.2308.7`.
Neither produces the described warning.

The reconstruction follows the snippet as closely as it can: `ddxRay`/
`ddyRay` are written in `RaygenShader` (both a member-wise and a
whole-struct cast-assignment version were tried), and `TraceRay` is
invoked one function away, through a helper like `TraceRadianceRay`. On
both compilers this compiles clean, with no `-Wpayload-access-trace`
warning at all.

Reading `SemaDXR.cpp` explains why, and it isn't the reported false
positive — it's the opposite problem. `raygeneration` shaders are given
a null `Info.Payload` (raygen has no incoming payload parameter, only a
local variable), and the entire "field never written for TraceRay call"
check — including the recursion needed to look inside a helper function
— is gated on `Info.Payload` being non-null. So for any `TraceRay` call
reached through a helper from raygen, that check never runs, whether or
not the fields are actually written. A [genuinely broken
control](https://godbolt.org/z/d1a7E9Mxj) (fields never written anywhere,
`TraceRay` called through the same kind of helper) confirms this: it
compiles silently on `dxc_trunk` too, where the same violation with a
*direct* `TraceRay` call does get diagnosed correctly.

So the snippet in this issue, reconstructed as written, doesn't produce
a false positive on either build — it produces no diagnostic at all,
correct or not. That could mean the real project code differs from the
snippet in some way that matters, or that the warning came from a
different configuration. Without the minimal repro requested above,
there isn't enough to tell which.

Suggest `needs repro steps` (a minimal, buildable case would settle
this) and `diagnostic`, alongside the existing `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5849](https://github.com/microsoft/DirectXShaderCompiler/issues/5849) Missing DXR PAQ indication in RDAT to determine whether MaxPayloadSizeInBytes needs validation

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#5849](https://github.com/microsoft/DirectXShaderCompiler/issues/5849).

Still reproduces on `main` (1.9.0.5465, `89e2f98e2`) and remains unresolved.

Compiling a minimal DXR library with a `[raypayload]`-qualified 20-byte payload
(`lib_6_7`, closesthit/miss/raygen all PAQ-annotated) and reading the RDAT
`FunctionTable` back directly (the `RuntimeDataFunctionInfo::PayloadSizeInBytes`
field), the size reported for `MyClosestHit`/`MyMiss` is `20` in *both* the
default PAQ-enabled build and a `-disable-payload-qualifiers` build — identical
either way. (Confirmed the PAQ-enabled build really does engage PAQs: it emits
`!dx.dxrPayloadAnnotations` module metadata that the disabled build lacks.) Also
checked `DxilFeatureInfo1`/`DxilFeatureInfo2` in full — there's no PAQ-related
feature bit either, so RDAT currently gives a runtime no signal of any kind that
PAQs were used on an entry point.

**History** — swept every cached stable release, `v1.4.1907` through `v1.9.2607`,
plus `main`. Releases before `lib_6_7` existed (`v1.4.1907`–`v1.6.2112`) fail with
`invalid profile lib_6_7`, as expected. Every release from `v1.7.2207`
(2022-07-18) onward — 14 data points total — agrees exactly with `main`: PAQ
usage is never reflected in RDAT. This isn't a regression with a bisectable
boundary; it's been this way since `lib_6_7` shipped.

**Source** — `lib/DxilContainer/DxilContainerAssembler.cpp` unconditionally
copies the shader's real payload size into the RDAT function record with no
PAQ-conditional branch anywhere nearby. No commit on any branch implements the
zeroing (or any other) fix discussed in this issue and its one reply, and
`tools/clang/test/DXC/disable_paq.hlsl` has no `PayloadSizeInBytes`/RDAT
assertion, so nothing would currently catch this either way.

Reading the thread, amarpMSFT's "option 3" agreement reads as referring to the
reporter's own closing line ("(3) zeroing the payload size looks like the best
option"), i.e. the same zero-RDAT-size proposal measured above — flagging this
interpretation since the issue body's own list is numbered 1/3/5, not 1/2/3.

Not reproducible on Compiler Explorer: the field lives in the `RDAT` container
part, and CE's DXC panes only show `-Fc`-style DXIL/IR text, which doesn't carry
this value.

Suggest keeping this open — it's a real, maintainer-agreed gap that has gone
dormant rather than being implemented or superseded.

**Labels:** current (`validation`) still fits; no change suggested.

<sub>Compiler was built from `main` at `89e2f98e2`; the local build self-reports a
different short SHA (`7665270b9`) because it was built from a fork of the same
tree — verified by `git diff --name-only` between the two, which shows zero
differing files.</sub>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
````

### Draft — [#5883](https://github.com/microsoft/DirectXShaderCompiler/issues/5883) Initializing a const-qualified var of type 'struct/array of (struct/array of) more than one type' with initializer 'init' will ignore any dynamic writes made to 'init' beforehand

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5883](https://github.com/microsoft/DirectXShaderCompiler/issues/5883).

Still reproduces on `main` (commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df),
self-reported version `1.9.0.5465`), and a release bisection shows it
always has: every stable release from `v1.4.1907` (2019, the oldest
release with a usable `dxc`) through `v1.9.2607` reproduces it, with no
clean release anywhere in between.

Compiling the repro's `const S a = {m};` branch still emits `m`'s
declaration-time constants into the buffer store, discarding the two
writes made to `m` beforehand:

```
call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 0, i32 undef, i32 42, i32 43, i32 44, ...)
call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 16, i32 undef, i32 45, i32 46, i32 47, ...)
```

The non-`const` variant on the same shader (`S a = {m};`, no `const`)
correctly emits the mutated values `1,2,3`/`4,5,6`, confirming the
const-qualified path specifically is at fault, as the original report
describes. Compiler Explorer's oldest DXC (1.6.2112) and current `dxc_trunk`
both show the same buggy payload: https://godbolt.org/z/s7WdTna8d

@amaiorano's root-cause analysis in this thread (the `EmitVarDecl` →
`EmitHLSLConstInitListExpr` → `ScanConstInitList` path in
`CGHLSLMS.cpp`) still matches the current source — the `DeclRefExpr` branch
of `ScanConstInitList` folds a referenced local variable's own declaration
initializer via `EmitConstantInit`, without checking whether that variable
was written again between its declaration and this read. Nothing in that
code path has changed since this was filed.

Suggested label: no change — `bug`, `correctness` and `matrix-bug` all
still fit (the January 2024 follow-up shows the same defect for
struct/array of any type, not only matrix, so `matrix-bug` covers one
manifestation rather than the whole scope, but nothing here justifies
removing it).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5924](https://github.com/microsoft/DirectXShaderCompiler/issues/5924) Cannot do swizzle operations with floating type when it's a typename

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5924](https://github.com/microsoft/DirectXShaderCompiler/issues/5924).

Still reproduces on `main` (commit `89e2f98e2`):

```
repro.hlsl:13:17: error: member reference base type 'float' is not a structure or union
        return t.xx;
               ~^~~
repro.hlsl:19:44: note: in instantiation of member function 'StyleClipper<float>::func' requested here
        return input.color + StyleClipper<float>::func(input.color.x).x;
                                                  ^
```

Confirmed the issue's workaround: declaring `func`'s parameter as literal
`float` instead of `float_t` makes the same `t.xx` compile cleanly. A plain
top-level `float t; return t.xx;` also compiles clean. So this is specific
to a swizzle whose base's *static* type is a template type parameter that
later resolves to a scalar, not to scalar swizzles in general.

Release history: unprobeable before v1.7.2308 (DXC's first release with
template support — earlier releases reject `template` itself), and
reproduces identically on every stable release from v1.7.2308 through
v1.9.2607 and on `main`; it has never worked in any template-capable
release.

@damyanp's comment above ("this _looks_ like it works in clang") checks out
under a controlled comparison: [Compiler Explorer](https://godbolt.org/z/h5q7acrv9)
shows the classic DXC frontend (`dxc_trunk`) failing with the diagnostic
above while the new Clang-based HLSL frontend (`hlsl_clang_trunk`) compiles
this exact source to DXIL, computing `t.xx` as `color.x + color.x`. Since
that comparison the `check-in-clang` label asked for is now answered,
suggest swapping it for `type-system` to track the observed
templated-vs-non-templated scalar member-access inconsistency.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5961](https://github.com/microsoft/DirectXShaderCompiler/issues/5961) Warnings about float to int conversions are wrong

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5961](https://github.com/microsoft/DirectXShaderCompiler/issues/5961).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`). Recompiling the
shader from the linked [Compiler Explorer example](https://godbolt.org/z/9PfEPYa3M) reproduces
the exact warning text quoted in the issue:

```
repro.hlsl:13:19: warning: implicit conversion from 'literal float' to 'int' changes value from 2147483648 to 2147483647 [-Wliteral-conversion]
    store(to_int(-2147483648.0)); // MaxNegative int: -2147483648
```

DXC's own DXIL output for the same compile constant-folds each `to_int`/`to_uint` call and
agrees with the source comments (`-2147483648`, `-2147483648`, `2147483647`, `0`,
`4294967295`), not with the warnings, on exactly the three lines whose literal has an explicit
unary minus. The root cause is in `Sema::AnalyzeImplicitConversions`
(`tools/clang/lib/Sema/SemaChecking.cpp`): when the source expression is a `UnaryOperator`
negating a `FloatingLiteral`, the code strips the minus and hands the **positive** literal to
`DiagnoseFloatingLiteralImpCast`, which then computes and prints both the "from" and "to"
numbers from that positive value — discarding the sign before the warning is even formatted.
Actual codegen evaluates the whole (negated) constant separately and gets it right, which is
why the two disagree only where a unary minus is involved.

This has been present in every stable release DXC has shipped (`bisect --linear`,
v1.4.1907..v1.9.2607, 20 releases, no invalid probes) and in [both CE's oldest DXC (1.6.2112)
and `dxc_trunk`](https://godbolt.org/z/95MndY74x) — it predates the report by several years and
is not something HLSL 202x's conforming-literals changes happen to fix either: retesting with
`-HV 202x` still prints a positive source value for negated literals (verified locally), it is
just wrapped in different-looking numbers because 202x also changes how these literals are
typed.

Labels (`bug`, `tech-debt`, `diagnostic`) still look right; no changes proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5971](https://github.com/microsoft/DirectXShaderCompiler/issues/5971) ASAN alloc\_dealloc\_mismatch false positive on Ubuntu Linux when using libc++ package

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5971](https://github.com/microsoft/DirectXShaderCompiler/issues/5971).

Not compiler-verifiable — the reported defect is in the platform C++ runtime's ASAN
interceptors, not in anything a compiled shader can exercise, so this triage is limited to
reading CI configuration and the linked upstream trackers. Checked against `main`
(`89e2f98e2`):

**The workaround from [#5976](https://github.com/microsoft/DirectXShaderCompiler/pull/5976) is
still in place, unchanged.** `azure-pipelines.yml` still sets
`ASAN_OPTIONS=alloc_dealloc_mismatch=0` for `check-all` on the Linux ASAN bot, exactly as that
PR added it. That PR's own commit message proposed a closing condition:

> Perhaps a future Linux image will include a build of libc++ that does not exhibit this false
> positive, at which point this workaround can be reverted.

**The toolchain has since moved off the originally-implicated package, but nobody has re-tested
the workaround.** At the time of #5976, the ASAN job used the OS-default `clang`/`clang++` (the
launchpad bug you cited is against Ubuntu's `llvm-toolchain-14` package). Today it runs on
Ubuntu-24.04 and explicitly installs `clang-18` + `libc++-18-dev` from `apt.llvm.org` rather
than any Ubuntu-default package. The `alloc_dealloc_mismatch=0` line carried forward through
that change without being revisited.

**Both upstream reports you linked are now closed:**
[llvm/llvm-project#59432](https://github.com/llvm/llvm-project/issues/59432) (closed
2024-12-21) and [llvm/llvm-project#52771](https://github.com/llvm/llvm-project/issues/52771)
(closed 2025-02-02) — the latter specifically about libc++ **from apt.llvm.org**, which is
exactly where DXC's CI now sources its libc++. Both closures predate today by well over a
year. This is suggestive that your second proposed fix path may already have happened for the
package DXC's CI actually uses now, but it isn't proof — confirming that needs someone with CI
access to actually remove the workaround and re-run the ASAN job (or an equivalent local
`libc++-18` + ASAN Linux build), which this triage pass couldn't do.

`tools/clang/test/DXC/recompile.test` (the test in your original log) still runs the same
`-dumpbin` call that reaches `DxcIncludeHandlerForInjectedSources::LoadSource`, so the exercised
code path hasn't changed.

Suggestion: worth someone with Linux ASAN-bot access trying a build with the
`ASAN_OPTIONS=alloc_dealloc_mismatch=0` workaround removed, now that the bot uses
`apt.llvm.org`'s clang-18/libc++-18 rather than the originally-affected package — given both
upstream reports are closed, there's a real chance the workaround can be dropped, but that
needs an actual CI run to confirm, not more reading.

Label suggestion: add `ci` and `sanitizer` (the taxonomy already defines both and neither is
applied); `linux` also fits, since the symptom is specific to the Linux/libc++ ASAN bot.

---
<sub>Triaged with AI assistance. This is a CI/toolchain-environment issue, so no compiler
output was produced or is relevant; the evidence is the current CI configuration and the
public state of the linked upstream issues. Please flag anything that looks wrong.</sub>
````

### Draft — [#5985](https://github.com/microsoft/DirectXShaderCompiler/issues/5985) DllMain calls LoadLibrary for dxil.dll, could cause deadlock or crash

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5985](https://github.com/microsoft/DirectXShaderCompiler/issues/5985).

The specific hazard reported here — `dxcompiler.dll`'s `DllMain` calling `LoadLibrary`
(via `DxilLibInitialize`) to load `dxil.dll` while holding the loader lock — is fixed on
`main` (checked at `89e2f98e2`, 2026-08-12).

`InitMaybeFail()` in `tools/clang/tools/dxcompiler/DXCompiler.cpp`, called from `DllMain` on
`DLL_PROCESS_ATTACH`, no longer calls `DxilLibInitialize()` at all, and the file no longer
includes `dxillib.h`. `DLL_PROCESS_DETACH` no longer calls `DxilLibCleanup`. `dxcompiler.dll`'s
validation now goes through a statically-linked, in-process validator
(`CreateDxcValidator` in `dxcutil.cpp`, "the locally-linked validator"), so there is no longer
any runtime dependency on loading `dxil.dll` from this DLL, from `DllMain` or otherwise.

Removed by commit `77b2ff676` ("NFC: remove dead external validation code paths from
dxcompiler", [PR #7451](https://github.com/microsoft/DirectXShaderCompiler/pull/7451), merged
2025-06-05): "DXC has now been changed to use the internal validator (loaded by
dxcompiler.dll) by default. This PR removes the ability for dxc.exe to load dxil.dll in
preparation for a series of changes to fix external validation handling." That commit is
confirmed to be 479 commits behind `main` at the checked commit (`gh api .../compare/...`),
so the fix predates this check by well over a year.

Two things from this thread remain open, for what it's worth:

- `tools/clang/tools/dxrfallbackcompiler/DXCompiler.cpp` (the DXR fallback-layer DLL) still has
  the identical pattern — `DllMain` still calls `DxilLibInitialize()`/`LoadLibrary` for
  `dxil.dll`. It's a much less commonly embedded binary than `dxcompiler.dll`, and this issue
  never named it, but it's the same defect in a sibling DLL.
- The broader ask to move the rest of `DllMain`'s work to `DxcCreateInstance*`, and the request
  for an explicit API to hand in a pre-loaded/pathed `dxil.dll`, are both still open — the fix
  took the narrower route of removing `dxcompiler.dll`'s own dependency on external `dxil.dll`
  validation rather than restructuring initialization more broadly.

Suggest: `crash` no longer applies to `dxcompiler.dll` specifically; `tech-debt` still fits
given the remaining `dxrfallbackcompiler.dll` instance and the unaddressed API asks in this
thread.

---
<sub>Triaged with AI assistance. This is a source/architecture issue, not a compile-time one,
so no compiler output was produced; the evidence is the current `DllMain` source, the fixing
commit's diff, and its ancestry relative to the checked commit. Please flag anything that
looks wrong.</sub>
````

### Draft — [#5987](https://github.com/microsoft/DirectXShaderCompiler/issues/5987) Error assigning struct into amplification payload

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5987](https://github.com/microsoft/DirectXShaderCompiler/issues/5987).

Still reproduces on `main` (Debug build, commit 89e2f98e2).

Compiling the repro with `-T as_6_7 -E main` crashes an assert-enabled build:

```
Error: 	!(onlyUsedByLifetimeMarkers(BCI))
File:
lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp(2630)
Func:	`anonymous-namespace'::SROA_Helper::RewriteBitCast.
	expected struct bitcast to only be used by lifetime intrinsics
```

On a Release-style build (no asserts compiled in), this surfaces as the reporter's exact
`error: llvm::cast<X>() argument of incompatible type!` — reproduced verbatim starting at
v1.7.2207, the oldest stable release that can even compile the `as_6_7` profile. Every
release before that rejects the profile outright (`invalid profile as_6_7`) rather than
avoiding the bug, so the history is: unmeasurable until `as_6_7` existed, then always
crashing since. [Compiler Explorer](https://godbolt.org/z/YoavsEvns) confirms the crash on a
current trunk build as well.

Both workarounds mentioned in the report were re-verified and do avoid the crash: commenting
out `payload.data = blah;`, and "unwrapping" `payloadType` so its members aren't a nested
struct — both compile cleanly. So the trigger is specifically assigning a whole struct value
into a member that is itself a struct, inside a `groupshared` amplification-shader payload.

Suggested labels: current `bug, dxil, crash` already fit; no change proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5993](https://github.com/microsoft/DirectXShaderCompiler/issues/5993) ClangTidy: clang-analyzer-core.uninitialized.Branch in third\_party/dawn/third\_party/dxc/tools/clang/tools/libclang/CIndex.cpp

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5993](https://github.com/microsoft/DirectXShaderCompiler/issues/5993).

Still present on `main` (commit `89e2f98e2`): `clang_createTranslationUnit` in
`tools/clang/tools/libclang/CIndex.cpp` is unchanged from what's quoted above (now at
lines 2947–2970, a small shift from unrelated edits elsewhere in the file, not from any change
to this code). `clang_createTranslationUnit2`'s active arm (`#if 1 // HLSL Change ... - no
support for serialization`) still returns `CXError_Failure` without ever assigning `*out_TU`,
so `clang_createTranslationUnit`'s `TU` local is still read (in the `assert`, and in
`return TU;`) without a path that guarantees it was initialized.

@llvm-beanz's suggested rewrite was implemented exactly in
[PR #6002](https://github.com/microsoft/DirectXShaderCompiler/pull/6002), opened by
@farzonl the day after this issue and approved — but it was never merged, and was closed
2026-01-22 by an inactivity sweep rather than by disagreement:

> This PR was closed as it has not been updated in the last two years. Please feel free to
> reopen if this PR should be merged and is in a reviewable state.

Reopening and rebasing #6002 is the cheapest path to closing this out.

For context: the flagged branch is dead code in every current DXC configuration (the `#if 1`
is unconditional), so this is a static-analysis/code-hygiene finding rather than an observed
runtime defect — consistent with `bug`/`tech-debt` already on the issue.

---
<sub>Triaged with AI assistance. This is a static-analysis/code-hygiene issue about source
outside the `dxc` build target, so no compiler was run; the evidence is the source text at the
cited commit and the linked PR/issue history. Please flag anything that looks wrong.</sub>
````

### Draft — [#5999](https://github.com/microsoft/DirectXShaderCompiler/issues/5999) An issue with template type deduction and globallycoherent?

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5999](https://github.com/microsoft/DirectXShaderCompiler/issues/5999).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`1.9.0.5465-triage`), consistent with @llvm-beanz's/@pow2clk's diagnosis above. Re-running the
distilled repro from [the CE link posted in this thread](https://godbolt.org/z/z4TnxrKqr):

```
repro.hlsl:18:5: warning: implicit conversion from 'globallycoherent RWByteAddressBuffer' to 'RWByteAddressBuffer' loses globallycoherent annotation [-Wconversion]
    TemplateFunction(SomeBuffer);
    ^
```

`ExplicitFunction(SomeBuffer)` (explicitly typed) still emits no warning, matching the original
asymmetry @simonwongms reported.

History floor: this repro shape is only probeable from v1.7.2308 (2023-08-14) onward, because
earlier releases fail with `'template' is a reserved keyword in HLSL` — HLSL function templates
didn't exist yet. Every stable release from v1.7.2308 through the current v1.9.2607 reproduces
it identically. [Updated CE link](https://godbolt.org/z/E16q13zKa) adds CE's oldest DXC (1.6.2112,
same template-keyword failure) alongside current trunk. I also tried the Clang-based HLSL front
end (`hlsl_clang_trunk`), since @llvm-beanz noted Clang implements attributes so they survive
canonicalization — but it doesn't yet parse `globallycoherent` for this repro, so it can't
answer that question right now.

The thread still describes this as the known qualifier-as-attribute canonicalization
limitation, and nothing in the linked comments points to a landed fix. Existing labels (`bug`,
`hlsl2021`, `shader-linking`, `type-system`) all still fit; no change proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#6001](https://github.com/microsoft/DirectXShaderCompiler/issues/6001) Pass-through control point case broken for hull shader

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6001](https://github.com/microsoft/DirectXShaderCompiler/issues/6001).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).

Compiling the repro from this issue (`HSPerPatchData` filled in with the
conventional tri-domain fields, since it isn't defined in the snippet above)
with `-T hs_6_0 -E MyHSMainPassthrough` still emits four
`dx.op.loadInput.f32` calls in `MyHSMainPassthrough`'s body and a non-null
`!dx.entryPoints` entry — exactly "Actual Behavior" as described: the
compiler does not recognize the pass-through case and still manually copies
every value.

```
%2 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 0, i32 %1)
%3 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 1, i32 %1)
%4 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 2, i32 %1)
%5 = call float @dx.op.loadInput.f32(i32 4, i32 0, i32 0, i8 3, i32 %1)
...
!5 = !{void ()* @MyHSMainPassthrough, !"MyHSMainPassthrough", !6, null, !16}
```

Bisected across every stable release from v1.4.1907 (2019-07) through
v1.9.2607 (2026-07): the behavior has never differed. This is a missing
optimization, not a regression. Compiler Explorer confirms the same output
on both `dxc_1_6_2112` and `dxc_trunk`:
https://godbolt.org/z/nM3en9K5b

The other two problems in the report (a validator crash on a hand-crafted
null-entry pass-through representation, and a validator false-positive on a
declaration-only entry) both require authoring a DXIL module by hand — no
`dxc.exe`-driven compile from HLSL reaches either code path, matching the
report's own note that no such module could be made to validate. Those
weren't independently re-verified here.

An external issue, `HansKristian-Work/dxil-spirv#263` (2025-11-05, closed),
independently describes this as still "a planned feature" in DXC, over a
year after this was filed.

No change from the label suggestion here — `bug`/`crash`/`validation` are
all supported by the report; the crash/validation content just isn't
reachable from a plain HLSL compile the way the missing-optimization part
is.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
````

### Draft — [#6003](https://github.com/microsoft/DirectXShaderCompiler/issues/6003) [Valgrind] Conditional branches on uninitialized SourceLocation::ID 

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6003](https://github.com/microsoft/DirectXShaderCompiler/issues/6003).

Re-checked both findings against `main` at commit `89e2f98e2` (built Debug, Windows; no
Valgrind/MSan-equivalent tool available in this environment).

**The `SemaHLSL.cpp:6465` out-of-bounds/uninitialised-index read (second finding) is confirmed
still fixed**, and was already fixed before this issue was filed: `108c34654` ("Fix asan stack
use after return (#5628)", 2023-09-14) added the bounds check
`if (pIntrinsic->pArgs[0].uTemplateId < MaxIntrinsicArgs)` around exactly the quoted line.
Reading `SemaHLSL.cpp` at `89e2f98e2` directly shows the same call site still guarded (now via
`CAB(pIntrinsic->pArgs[0].uTemplateId < MaxIntrinsicArgs, 0);`), so this stays fixed on current
`main`.

**The `TypeLoc::getBeginLoc()` uninitialised-value finding (first finding) is unconfirmed, not
fixed-looking.** `clang::TypeLoc::getBeginLoc()` (`TypeLoc.cpp`) and the
`TreeTransform`/`SubstType`/`TemplateDeclInstantiator` chain above it are unmodified since
import, and no commit touching `NewSimpleAggregateType`, `GetOrCreateVectorSpecialization` or
`LookupVectorType` in `SemaHLSL.cpp` (the HLSL-side caller that synthesizes the vector
template's `FieldDecl`s) addresses source-location initialisation. Compiling the repro on the
Windows ground-truth build (both the filed SPIR-V command and a DXIL-targeted variant) exits 0
with no crash either way — consistent with Valgrind's own report, which is a conditional-jump
warning on "still reachable" memory, not a fault a plain run would show. Without a
Valgrind/MSan-capable build to re-run, this can't be confirmed fixed or refuted in this
environment.

Labels (`bug`, `sanitizer`) already fit; no change suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#6005](https://github.com/microsoft/DirectXShaderCompiler/issues/6005) [Assert Triggered] MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking"

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6005](https://github.com/microsoft/DirectXShaderCompiler/issues/6005).

Still reproduces on `main` (commit `13730886e`) in an assert-enabled Debug build, using the
exact command line and source @s-perron posted above:

```
Error: assert(MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking")
File:
<repo>/tools/clang/lib/Sema/SemaDecl.cpp(11156)
Func:   clang::Sema::ActOnFinishFunctionBody
```

Same assert, file and function @s-perron reported (their build hit line 11119; the ~2-year
drift to 11156 is unrelated `SemaDecl.cpp` edits, not a different assert). Confirmed
independent of `-spirv`: removing it trips the same assert compiling to DXIL. Continuing past
the assert (i.e. running the code path a Release build's compiled-out assert takes) still
produces a well-formed SPIR-V module — consistent with the original report that the shader
compiles despite the assert.

Every stable release from v1.7.2207 onward compiles this cleanly, but that is not evidence of
a fix: all release binaries are Release builds, and `assert()` is compiled out under `NDEBUG`,
so a Release binary structurally cannot show this symptom. The same applies to Compiler
Explorer, which only runs Release builds:
https://godbolt.org/z/h7WEM3v8G (the shared page states this limitation). No older
assert-enabled build was available in this session to check when the assert was introduced.

Releases through v1.6.2112 can't run this particular command at all (`-HV 202x`/HLSL 2021
predates them: `Unknown HLSL version: 202. Valid versions: 2016, 2017, 2018, 2021`) —
unrelated to this bug.

Suggest adding `crash` (assert-only crash, currently missing) and `type-system` (triggered by
a user-namespace typedef whose name collides with the type produced by HLSL's own builtin
`vector<T,N>`/`matrix<T,R,C>` templates).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#6016](https://github.com/microsoft/DirectXShaderCompiler/issues/6016) Using large vert/hull/domain IO makes DXC crash when building to DXIL

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6016](https://github.com/microsoft/DirectXShaderCompiler/issues/6016).

Still reproduces on `main` (Debug build at commit `89e2f98e2`, 2026-08):

```
error: Failed to allocate all input signature elements in available space.
UNREACHABLE executed at lib\HLSL\HLSignatureLower.cpp:523!
```

Bisecting the released binaries, this regressed between v1.7.2207 (last good) and v1.7.2212
(first bad). Through v1.7.2207 the same detected condition was an ordinary diagnosed error:

```
repro.hlsl:19:1: error: Failed to allocate all input signature elements in available space.
repro.hlsl:19:1: error: Failed to allocate all output signature elements in available space.
```

That matches @tex3d's diagnosis in this thread exactly: `21e56159e` ("Add diagnostic
tests (#4599)") is inside the v1.7.2207..v1.7.2212 window and is the only commit in that
window touching `HLSignatureLower.cpp`, so it is confirmed as the regressing change, not just
plausible. `main`'s `AllocateDxilInputOutputs()` still routes both the input- and
output-signature allocation-failure checks to `llvm_unreachable` (`HLSignatureLower.cpp:521-531`),
so the fix described in the thread — restoring these to diagnosed errors — has not landed.

Compiler Explorer: https://godbolt.org/z/h7YxEKKT5 (CE's oldest DXC, 1.6.2112, still gives the
clean diagnostic; `dxc_trunk` crashes the process outright — SIGSEGV rather than the
reporter's SIGABRT, since CE's build has asserts compiled out, but a crash either way).

Per this thread, no shader-model change is being requested — everyone agrees this much
packed IO is a legitimate limit. Suggest keeping this open and labeled as-is
(`bug`, `crash`, `diagnostic`, `incorrect-code` all still fit); the remaining work is turning
the `llvm_unreachable` back into the diagnostic it used to be.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#6073](https://github.com/microsoft/DirectXShaderCompiler/issues/6073) Non-const static data members of templated structs fail to compile

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6073](https://github.com/microsoft/DirectXShaderCompiler/issues/6073).

Still reproduces on `main` and on every stable release that can parse HLSL
templates at all (v1.7.2308 through v1.9.2607, the latest).

On the shipping release binaries (asserts compiled out), the repro produces
the exact text quoted in this issue, byte-for-byte, including the mangled
name:

```
Declaration may not be in a Comdat!
i32* @"\01?Num@?$Test@$0CK@@@2HA"
```

On a Debug build this same repro instead crashes earlier, in
`clang::LinkageComputer::getLVForDecl` (a Debug-only assert), before ever
reaching that verifier check -- confirmed to be the same defect by continuing
the debug session past that assert (which is what a Release build does since
the check compiles out) and observing it land on the identical Comdat text.

Both patterns this issue says already work (a non-templated struct with a
non-const static member, and a templated struct with a `static const`
member) still compile cleanly, matching the report.

Releases older than v1.7.2308 don't support HLSL templates yet, so they can't
run this repro at all -- they're not evidence of anything, including a fix.
No release has ever compiled this pattern.

[Compiler Explorer](https://godbolt.org/z/17nh9j5fW): the oldest DXC there
predates templates, and `dxc_trunk` fails with `LLVM ERROR: Broken module
found, compilation aborted!` (matching the local release measurement, though
CE's pane doesn't surface the intermediate Comdat line).

Given @llvm-beanz's comment that a durable fix may need a language change,
consider adding `hlsl-next` alongside the existing `bug`/`crash`/`correctness`
labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#6082](https://github.com/microsoft/DirectXShaderCompiler/issues/6082) Incorrect DXIL bitcasts generated for bool matrices in ray payloads 

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6082](https://github.com/microsoft/DirectXShaderCompiler/issues/6082).

Confirmed: the reported IR shape still reproduces on `main`
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`) and is unchanged all the way back to v1.6.2104,
the oldest release that accepts `-T lib_6_6` (v1.4.1907 and v1.5.2010 predate that profile).
`dxc -T lib_6_6` on the repro still emits:

```llvm
%class.matrix.bool.1.2 = type { [1 x <2 x i1>] }
...
  %2 = bitcast %class.matrix.bool.1.2* %1 to <2 x i32>*
  %3 = load <2 x i32>, <2 x i32>* %2, align 4
```

byte-for-byte identical to the issue body, on the current build, on CE's oldest DXC
(`dxc_1_6_2112`), and on `dxc_trunk`:
https://godbolt.org/z/zxjbnx5dE

For contrast, a `bool2` **vector** field in the same payload struct does not hit this pattern
— it's already represented directly as `<2 x i32>` with a plain integer load, no bitcast.
Only bool **matrices** take this path.

DXC's own validator accepts this output with no errors or warnings, which lines up with
@llvm-beanz's point above: this isn't a claim about DXIL being invalid by DXC's own rules,
only about what happens if the container is reinterpreted as standard/modern LLVM IR (as the
follow-up `opt -passes="vector-combine,instcombine"` example does) — and that reinterpretation
is exactly what the reporter's real-world reproducer relies on.

This needs the design discussion the thread was already heading toward rather than a compiler
fix-or-close decision based only on repro status. The last comment (2024-04-10) was waiting on
@tex3d; nothing
has landed here since, and the only related activity is upstream, in the new LLVM-based HLSL
frontend (`llvm/llvm-project#91639`, "[HLSL] Boolean vector support"), consistent with
@llvm-beanz's stated plan to handle DXIL→valid-LLVM-IR legalization there rather than in this
repository.

Suggested label additions: `correctness`, `matrix-bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#6084](https://github.com/microsoft/DirectXShaderCompiler/issues/6084) [CI] Add clang-cl on windows build to test pipeline

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6084](https://github.com/microsoft/DirectXShaderCompiler/issues/6084).

This is a CI/pipeline request rather than a compiler-behaviour bug, so it was
checked against the pipeline definition rather than by compiling a shader.

At current `main` (`89e2f98e2`), `azure-pipelines.yml` has no `clang-cl` build
job at all — not even the release-only one the issue describes — and none of
the `.github/workflows/` files build DXC either. The `x64-clang-cl-*` presets in
`CMakeSettings.json` are local Visual Studio configurations, not something CI
exercises.

PR [#6107](https://github.com/microsoft/DirectXShaderCompiler/pull/6107) ("Fixes:
#6084") would have added this, including a follow-up commit toward "normal"
(non-release) builds as this issue asks for. It was never merged; it was closed
on 2026-01-22 by a maintainer as part of a stale-PR sweep ("has not been updated
in the last two years"), not because the change was rejected or done elsewhere.

So the request is still fully open: no clang-cl Windows build exists in CI today,
and the prior attempt to add one lapsed for inactivity rather than being
resolved. `enhancement` and `ci` both still look right; no label change
proposed.

---
<sub>Triaged with AI assistance. Findings were verified by reading the CI
pipeline definition at the cited commit and the public issue/PR history; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- Drafts are unposted and require maintainer review. Nothing was applied to any issue: no
  comment, label, close, reopen, or reaction. Every label suggestion in every draft above is a
  proposal, recorded through `verdict.json`'s `labels_add`/`labels_remove` fields and never
  applied.
- This is a single, contiguous age slice of 100 issues (see **Headline**); no general
  conclusion about the current backlog follows from it.
- 7 close-fixed recommendations rest on release-level measurement back to each issue's own
  bisection floor, corroborated by Compiler Explorer; none rests on a build-verified single
  commit — see **Limitations**.
- The `#5704` stale-output-file finding means any *other* multi-line-`cmd.txt` issue triaged
  before this session's fix, in this batch or an earlier one, was not re-swept to look for the
  same signature beyond the four structurally-similar issues checked in \*\*The #5704
  stale-output-file cross-release contamination hazard\*\* — those four showed no evidence of it,
  but a corpus-wide re-verification of every historical multi-line capture was out of scope for
  this batch.
- The existing-issue refresh (**Existing-issue refresh**) is a metadata/comment snapshot
  comparison only; it does not imply any of the 107 issues' underlying compiler behaviour was
  re-measured.
- No DXC source was modified. No commit was made. Nothing was pushed.

