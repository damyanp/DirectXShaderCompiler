# DXC issue triage — batch 009

**Ground truth:** clean `main` **Debug** build,
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`.
All five verdicts record `triaged_with_commit: 13730886e` — corrected after the fact; they
originally recorded `ab5400907`, which the binary self-reports.

The registered SHA was removed by a message-only history rewrite. Its live twin is
`950b58792`; both have tree `574a2bd25a0b57ea1f450ea3dc0776919fcfe108`. At batch open,
upstream `main` was `13730886e`, and
`git diff --name-only ab5400907 FETCH_HEAD` found no files outside this triage skill. The
binary therefore still represents compiler source identical to upstream `main` and was not
rebuilt.

**Nothing was posted, edited, labelled, closed, committed or pushed. No DXC compiler source
was modified.** `reindex` was deliberately not run, so this batch had no retroactive
re-scoring; `audit` checked completeness only.

## Headline

All five issues still reproduce, but they resolve into different kinds of backlog work:

- #2633 is a partially implemented SPIR-V capability request: export works, import does not.
- #3237 exposes an API surface whose parameter-reflection records were never implemented.
- #3429 is an optimizer/validator mismatch around an unambiguous TGSM pointer `phi`.
- #3695 remains a deterministic compiler crash on invalid source.
- #3706 is a policy decision: the front-end warning exists but is disabled by default, and
  enabling it would not cover the tested partially initialized form.

The batch's highest-value immediate finding is textual: **#2633's 2020 maintainer answers are
partly stale.** They say relocatable SPIR-V/linkage generation does not exist, but the export
direction has emitted `LinkageAttributes Export` since v1.6.2104. The 2024 design comment is
still accurate and is explicitly excluded from the staleness finding.

## Summary

| # | Title | Repro | Status | History | Suggested action | Compiler Explorer |
| --- | --- | --- | --- | --- | --- | --- |
| [#2633](https://github.com/microsoft/DirectXShaderCompiler/issues/2633) | [SPIRV][Question]Link libraries ⚠️ | agent-constructed | **repros** | import absent in 19 SPIR-V-capable releases; export present since v1.6.2104 | enhancement, not bug | [ca49jMrrc](https://godbolt.org/z/ca49jMrrc) |
| [#3237](https://github.com/microsoft/DirectXShaderCompiler/issues/3237) | Library Reflection: Listing parameters return E_FAIL | partial | **repros** | 21/21 measured releases plus `main` | keep open | n/a — API is unreachable from `dxc.exe` |
| [#3429](https://github.com/microsoft/DirectXShaderCompiler/issues/3429) | DXC Validation Error: TGSM pointers must originate from an unambiguous TGSM global variable | complete | **repros** | all 20 bisectable releases | keep open | [61Gb43GjM](https://godbolt.org/z/61Gb43GjM) |
| [#3695](https://github.com/microsoft/DirectXShaderCompiler/issues/3695) | DXC Crash on Bad Shader | complete | **repros** | all 20 bisectable releases | keep open | [aqPedMGE4](https://godbolt.org/z/aqPedMGE4) |
| [#3706](https://github.com/microsoft/DirectXShaderCompiler/issues/3706) | Passing uninitialized var as index to structure buffer causes undef being passed in dxil | complete | **repros** | all 20 bisectable releases | needs maintainer judgement | [n9YeYKT3W](https://godbolt.org/z/n9YeYKT3W) |

Confidence is `high` on all five. Four CE links were independently read back during the open
phase. #3237 is a deliberate skip: Compiler Explorer can run `dxc.exe`, but cannot load each
release's `dxcompiler.dll` and call
`ID3D12FunctionParameterReflection::GetDesc`; the committed harness provides that evidence.

## Per-issue findings

### #2633 — one half landed; the remaining half is a design request

`export float4 foo(...)` under
`-T lib_6_3 -spirv -fspv-target-env=universal1.5` emits:

```text
OpCapability Linkage
OpDecorate %foo LinkageAttributes "foo" Export
```

That first appears in v1.6.2104. The evidence points to `5ae95866e` / PR 3234, the only commit
in the 268-commit window touching `HLSLExportAttr` in the SPIR-V backend or
`Capability::Linkage`, but that commit was not built in isolation.

The import half still fails on `main` and all 19 SPIR-V-capable releases:

```text
repro.hlsl:27:21: error: found undefined function
```

Source corroborates the asymmetry: the SPIR-V front end has one
`LinkageType::Export` call site and zero `LinkageType::Import` call sites. Clang trunk emits
both decorations for the same source, while using a different symbol-mangling convention.
The remaining questions are the import decoration, globals, linking order and `lib_6_x`
compatibility. `enhancement-not-bug` is therefore appropriate.

**Text staleness:** set, and collation agrees. The 2020 answers are false for the export
direction; the 2024 design comment remains current.

### #3237 — a never-populated reflection API, not a regression

A committed C++ harness calls the exact COM path reported by the issue. On `main` and all 21
measured release DLLs:

```text
D3D12_FUNCTION_DESC.FunctionParameterCount=0
ID3D12FunctionParameterReflection::GetDesc(param 0) -> 0x80004005 (E_FAIL)
```

`CFunctionReflection::GetFunctionParameter` ignores the index and returns an invalid singleton
whose `GetDesc` always returns `E_FAIL`; the count and return fields are marked `// Unset:`;
and `RuntimeDataFunctionInfo` in `RDAT_LibraryTypes.inl` contains no parameter records. The
stub is unchanged since `c1b662784` (2018-04-11).

The issue-body source needs `export` before the reported call is reachable. Without it,
reflection reports zero functions on all 21 releases. This is a repro-completeness gap, not
stale issue text: adding `export` reaches the API and reproduces exactly.

### #3429 — an unambiguous `phi` is rejected without examining its inputs

All 20 bisectable releases and `main` reject the shader with E_FAIL. With `-Vd`, both incoming
values of each `phi float addrspace(3)*` are GEPs into the same groupshared global. In
`lib/DxilValidation/DxilValidation.cpp`, the back-walk applies only when the instruction is
itself a GEP or bitcast; a pointer-typed `phi` falls directly into the rejection branch.
`dxv.exe` built from the same tree independently rejects the emitted module.

Optimization creates the rejected shape: `-Od` and `-O0` compile; `-O1`, `-O2` and `-O3`
fail. At `-O0` no groupshared-pointer `phi` is formed.

The first predicate falsely reported a v1.5.2010 transition because v1.4.1907 prints the same
rule without the modern `error:` prefix or source location. Matching the stable rule text
removes the false boundary.

### #3695 — deterministic across Debug, Release, Windows and Linux

The attached shader still crashes `main`. Debug exits `0xE0000001` at
`DxilLowerCreateHandleForLib::ReplaceResourceUserWithHandle`; all 20 measured release builds
access-violate with `0xC0000005`. v1.4.1907 and v1.5.2010 produce empty stdout and stderr, so a
message-based crash predicate would have invented a fix.

The body guesses that assigning one global `RWTexture2D` to another is the trigger. That
straight assignment is diagnosed. The committed 10-line crashing reduction instead passes a
resource through a resource-returning function and assigns it back to the same global; the
different-global variant is also diagnosed. Clang rejects the source with a located
diagnostic.

**Text staleness:** deliberately not set, and collation agrees. The body hedges its trigger
description, and its attached repro still crashes on the first run. The minimization refines
the trigger without making the issue text misleading.

### #3706 — the analysis exists, but default policy and coverage remain open

All 20 measured releases and `main` exit 0 without a diagnostic and emit `undef` in the
structured-buffer index operand. Local controls prove the module validates and that the
predicate is not confusing the index with the structurally `undef` element-offset slot used
by a valid `ByteAddressBuffer`.

`-Wall` produces the existing literal diagnostic:

```text
warning: variable 'j' is uninitialized when used here [-Wuninitialized]
```

`warn_uninit_var` is `DefaultIgnore`. However, the tested partially initialized form
(`int2 j; j.x = 1; stbuf[j.y]`) remains silent under `-Wall` while emitting the same `undef`
index. FXC rejects the original source with `error X4000`. The maintainer decision is whether
to enable the warning, add validator coverage, or make this a language-level error.

## Cross-issue analysis

### #2633 and #3237 — the same history, correctly different actions

Both are “never implemented” findings, but that fact alone should not determine the action.

- #2633 asks for a new capability and is already labelled `enhancement`; the thread records
  unresolved design questions, and no existing SPIR-V import path promises to work.
- #3237 exposes an existing public reflection method that returns an unconditional failure,
  while adjacent descriptor fields and the D3D11 counterpart establish the expected shape.
  The implementation was deliberately scoped, but the API gap is still a valid open issue.

The actions are therefore consistent: `enhancement-not-bug` for #2633 and
`still-valid-keep-open` for #3237. The shared backlog recommendation is to record
“never implemented / capability gap” separately from “regression”, then classify by contract:
new design request, existing-but-stubbed API, or once-working defect. Chronology alone is not
the taxonomy.

### #3706 and #3009 — related, not duplicates

Collation agrees with the worker's conclusion.

1. The existing front-end warning catches #3706's wholly uninitialized scalar under `-Wall`
   but is silent on the tested partially initialized `int2` shape corresponding to #3009.
   Enabling it by default would close the filed #3706 case and leave #3009 open.
2. Their DXIL manifestations need different checks: #3009 feeds `undef` to arithmetic
   (`IMad`/`FMad`), while #3706 feeds it to a resource index beside an operand where `undef`
   can be mandatory.
3. Maintainer routing supports, but does not prove, the distinction: the issues carry
   different validation history, and the strict-validator proposal cites #3706 specifically.

The first two are technical grounds; the third is corroborating backlog evidence. A
cross-reference may help discoverability, but `duplicate-of #3009` would erase a real
difference in both front-end coverage and validator design.

### Repeated tooling traps

Independent workers repeatedly paid the same costs:

- **`godbolt-note.txt` is auto-commented by the tool.** #3429, #3695 and #3706 each initially
  produced double `//` prefixes.
- **The console's one-line CE summary hides decisive output.** #2633 and #3695 both needed the
  full pane capture to find the useful Clang result.
- **Hand-written evidence bypasses path redaction.** Machine-specific paths appeared across
  #2633, #3237, #3429 and #3695 through harness output, hand captures or script defaults.
  `triage.py` redacts its own headers, not arbitrary subprocess text.
- **Shell hand-probes are less trustworthy than argv-based runs.** #2633 found PowerShell
  argument splitting and stale `$LASTEXITCODE`; #3429 hit backtick expansion; #3237 found a
  batch-parser close-parenthesis hazard. Each can return plausible output or exit 0.

The agent search false-zero was also independently corrected by the #3429 worker after the
orchestrator's first diagnosis. The trigger is a missing glob filter, not the hidden directory.
All meaningful absence checks in collation used `Select-String` instead.

## Summaries checked against their evidence

Every `summary` and `text_stale` field was read as a separate pass against its own `notes.md`.
No verdict changed. The following exact replacements tightened scope or removed causal
overstatement:

- **#2633**
  - Current: `Remaining step is the design decision in the thread, not a defect.`
  - Replacement: `The next action is the design decision in the thread; this is a capability request, not a defect.`
- **#3237**
  - Current: `driving each release own dxcompiler.dll`
  - Replacement: `driving each release's own dxcompiler.dll`
- **#3429**
  - Current: `no probeable release has ever compiled it`
  - Replacement: `none of the 20 measured release binaries compiled it`
  - Current: `scores healthy releases as no-repro`
  - Replacement: `scores reproducing probes as no-repro`
- **#3695**
  - Current: `on all 20 releases v1.4.1907..v1.9.2607`
  - Replacement: `on all 20 bisectable releases measured from v1.4.1907..v1.9.2607`
  - Current: `every release access-violates`
  - Replacement: `all 20 access-violate`
  - Current: `the crash needs the round trip through a resource-returning function back into the same global`
  - Replacement: `the 10-line crashing reduction uses a round trip through a resource-returning function back into the same global`
- **#3706**
  - Current: `in all 20 releases v1.4.1907..v1.9.2607`
  - Replacement: `in all 20 bisectable releases measured from v1.4.1907..v1.9.2607`
  - Current: `it does not fire on a partially-initialized index`
  - Replacement: `it does not fire on the tested partially-initialized int2 index`

The #2633 `text_stale` field is supported and narrowly scoped. No other issue warrants that
field.

## Step-10 independent draft review

`GPT (collation)` reviewed all five drafts after reading their notes. Concision was the primary
criterion; no technical diagnostic, version, symbol, file name, IR snippet or staleness finding
was removed. Accepted replacements:

### #2633

1. **Current**

   > DXC rejects the unresolved call rather than emitting an `Import` decoration, so there
   > is nothing for `spirv-link` to resolve against. There is no way around it from user
   > code that I could find: `-default-linkage external` is DXIL-only, `dxc -link` accepts
   > DXIL containers only (`Invalid DXIL container`), and inline SPIR-V cannot express
   > `LinkageAttributes` because `[[vk::ext_decorate]]` takes only integers and
   > `[[vk::ext_decorate_string]]` only strings, while that decoration needs both.

   **Replacement**

   > DXC rejects the unresolved call rather than emitting an `Import` decoration, so there
   > is nothing for `spirv-link` to resolve against. I found no user-code workaround:
   > `-default-linkage external` is DXIL-only; `dxc -link` rejects SPIR-V as
   > `Invalid DXIL container`; and the inline attributes split integer and string operands,
   > so neither can express `LinkageAttributes`.

2. **Current**

   > Worth noting for whoever picks the design up: **clang's HLSL SPIR-V backend already
   > emits both decorations** for this same source, and needs no `universal1.5` to do it.
   > It names symbols with Itanium mangling (`_Z3fooDv4_f`) where DXC uses the plain source
   > name (`foo`), so the two would not currently resolve each other's symbols.

   **Replacement**

   > **Clang's HLSL SPIR-V backend emits both decorations** for the same source without
   > `universal1.5`. It uses Itanium mangling (`_Z3fooDv4_f`) versus DXC's plain source name
   > (`foo`), so their modules would not currently resolve each other's symbols.

3. **Current**

   > The remaining step is the design decision @s-perron set out in
   > [this comment](https://github.com/microsoft/DirectXShaderCompiler/issues/2633#issuecomment-2253075613)
   > — the `Import` decoration, what to do about global variables, and `lib_6_x`
   > backwards compatibility. That is a product and language call, not something triage
   > should pre-empt, and nothing here should be read as a commitment to implement it.

   **Replacement**

   > The remaining design questions are the `Import` decoration, global variables, and
   > `lib_6_x` backwards compatibility, as @s-perron set out in
   > [this comment](https://github.com/microsoft/DirectXShaderCompiler/issues/2633#issuecomment-2253075613).
   > Triage does not decide them or imply an implementation commitment.

### #3237

1. **Current**

   > **Still reproduces on `main`** (`ab5400907`; `dxcompiler.dll` reports
   > `1.9.0.5433`), and on all 21 releases I could measure, **v1.4.1907
   > (2019-07-15) through v1.9.2607 (2026-07-29)** — no version behaves
   > differently.

   **Replacement**

   > **Still reproduces on `main`** (`ab5400907`; `dxcompiler.dll` reports
   > `1.9.0.5433`) and on all 21 releases I could measure, **v1.4.1907
   > (2019-07-15) through v1.9.2607 (2026-07-29)**.

2. **Current:** `Four things in the tree, all at ab5400907:`

   **Replacement:** `On ab5400907:`

3. **Current**

   > I have not touched the open question from #657 — how much this is worth to
   > developers who want it — which looks like the actual blocker here rather than
   > anything about the diagnosis.

   **Replacement**

   > Whether this is worth implementing remains the product question raised in
   > #657; these measurements do not address priority.

### #3429

1. **Current**

   > Still reproduces on `main` (dxc 1.9.0.5433, commit `ab5400907`, Debug), and on **all 20
   > release binaries from v1.4.1907 (2019-07) through v1.9.2607 (2026-07)** — every release I can
   > still run rejects it, and v1.4.1907 is the oldest I have a binary for.

   **Replacement**

   > Still reproduces on `main` (dxc 1.9.0.5433, commit `ab5400907`, Debug), and on **all 20
   > bisectable release binaries measured from v1.4.1907 (2019-07) through v1.9.2607
   > (2026-07)**.

2. **Current**

   > - **v1.4.1907 reports the same rule in an older format** — `at 0x… inside block … of function
   >   main TGSM pointers must originate…`, with no `error:` prefix and no source location. Worth
   >   knowing when searching old reports; [#2768](https://github.com/microsoft/DirectXShaderCompiler/issues/2768)
   >   (2020) carries the same wording.

   **Replacement**

   > - **v1.4.1907 reports the same rule without the `error:` prefix or source location**, instead
   >   printing `at 0x… inside block … of function main TGSM pointers must originate…`;
   >   [#2768](https://github.com/microsoft/DirectXShaderCompiler/issues/2768) preserves the same
   >   older wording.

3. **Current**

   > For what it is worth, `hlsl_clang_trunk` compiles this source and never forms a merged
   > groupshared pointer — it keeps the address computation inside each branch (pane 4 of the link;
   > checked against a control shader under the same flags). Clang does not run the DXIL validator,
   > so that is a statement about what it emits, not about what the rule would accept.

   **Replacement**

   > `hlsl_clang_trunk` compiles this source without forming a merged groupshared pointer; it keeps
   > the address computation inside each branch (pane 4, checked against a control under the same
   > flags). Clang does not run the DXIL validator, so this describes its output, not what the rule
   > would accept.

### #3695

1. **Current**

   > **Still reproduces.** The attached `shader.txt` crashes `main` at `1.9.0.5433` (`ab5400907`)
   > with the filed command line, and crashes every release binary from v1.4.1907 to v1.9.2607.

   **Replacement**

   > **Still reproduces.** The attached `shader.txt` crashes `main` at `1.9.0.5433` (`ab5400907`)
   > with the filed command line, and all 20 bisectable release binaries measured from v1.4.1907
   > to v1.9.2607.

2. **Current**

   > All 20 releases v1.4.1907..v1.9.2607 were probed individually and all 20 crash, so there is no
   > window in which this worked. Worth knowing for anyone else testing it: **v1.4.1907 and v1.5.2010
   > crash with no output at all** — empty stdout and stderr, exit `0xC0000005`.

   **Replacement**

   > All 20 measured releases crash. **v1.4.1907 and v1.5.2010 produce no output at all** — empty
   > stdout and stderr, exit `0xC0000005`.

3. **Current:** `What crashes is passing a global resource to a function that returns it and assigning the result back to **the same** global. Ten lines, same arguments:`

   **Replacement:** `The 10-line crashing reduction passes a global resource through a function and assigns the result back to **the same** global:`

4. **Current:** `Assigning to a *different* global via the same function is diagnosed, not crashed.`

   **Replacement:** `The straight assignment and the different-global function variant are diagnosed, not crashed.`

5. **Current:** `The Clang pane is the interesting one: it rejects the same source cleanly, with a location.`

   **Replacement:** `Clang rejects the same source cleanly, with a location:`

### #3706

1. **Current**

   > Still reproduces on `main` (1.9.0.5433, `ab5400907`), and in all 20 releases from v1.4.1907
   > through v1.9.2607 — including v1.6.2104, which shipped two days before this was filed.

   **Replacement**

   > Still reproduces on `main` (1.9.0.5433, `ab5400907`) and in all 20 bisectable releases measured
   > from v1.4.1907 through v1.9.2607, including v1.6.2104, which shipped two days before filing.

2. **Current**

   > `warn_uninit_var` is `DefaultIgnore` in `DiagnosticSemaKinds.td`, inherited from upstream
   > Clang, so it is reached only via `-Wall`/`-Wuninitialized`.

   **Replacement**

   > `warn_uninit_var` is `DefaultIgnore` in `DiagnosticSemaKinds.td`; `-Wall` or
   > `-Wuninitialized` enables it.

3. **Current**

   > On the validator: it does police this value, but only as one *stored* to a UAV
   > (`Instr.UndefinedValueForUAVStore`). `RawBufferLoad` validation inspects the `elementOffset`
   > and alignment operands and never the index. Worth knowing if anyone tests for this: `undef`
   > alone is not a usable signal here — for a ByteAddressBuffer the `elementOffset` operand of the
   > very same op is *required* to be `undef` (`Instr.CoordinateCountForRawTypedBuf`), so the slot
   > matters.

   **Replacement**

   > The validator rejects `undef` stored to a UAV (`Instr.UndefinedValueForUAVStore`), but
   > `RawBufferLoad` checks `elementOffset` and alignment, not the index. The slot matters: for a
   > ByteAddressBuffer, `elementOffset` on the same op must be `undef`
   > (`Instr.CoordinateCountForRawTypedBuf`).

4. **Current**

   > What should happen is a design decision rather than a measurement, and there appear to be
   > three separable options — enable the existing warning by default, add a validator rule, or
   > make it a language-level error as FXC did. `microsoft/hlsl-specs#272` already tracks the
   > validator option and cites this issue.

   **Replacement**

   > The policy choice is among enabling the warning by default, adding a validator rule, or making
   > this a language-level error as FXC did. `microsoft/hlsl-specs#272` tracks the validator option
   > and cites this issue.

Every accepted replacement was read back against the evidence. In particular, literal
diagnostics stayed verbatim, #3429's old-format warning stayed actionable, and #3706's
partial-initialization caveat was retained.

## What this batch taught about the method

1. **“Never implemented” needs its own backlog dimension.** It describes both a new capability
   request and a stubbed public API, but those deserve different actions. Record implementation
   history separately from contract and product priority.
2. **A harness-as-compiler still cannot be release-swept safely by `bisect`.** #3237 is the
   fourth occurrence. Running ordinary `bisect` would have returned the exact opposite
   history because `dxc.exe` never calls the API. The tool should eventually refuse or accept
   a per-release harness template.
3. **Diagnostic framing is not stable history evidence.** #3429's `error:` prefix created a
   false transition. Match the stable rule text and inspect isolated endpoint disagreements.
4. **Claims that a control exists need a named artifact.** #3706's worker found that #3009's
   predicate note claims a negative control that was never committed. `audit` cannot infer a
   missing file from prose.
5. **Path hygiene needs a mechanical gate and a positive control.** Manual artifacts and
   harness stdout bypass the runner's redaction, and both the orchestrator and a worker wrote
   patterns that missed one escaping form before validating against known-positive input.
6. **Repeated worker costs identify tool defects.** Three workers independently hit note
   auto-commenting; two independently had useful CE output hidden after line one. These are
   stronger signals than a single method note.

No method lesson was promoted into `SKILL.md` or `scripts/` during collation because the
orchestrator already has edits in flight there. Recommendations are recorded here rather than
creating an overlapping change.

## Proposed labels

None applied.

| # | Current | Proposed additions |
| --- | --- | --- |
| 2633 | `enhancement`, `spirv` | `question` |
| 3237 | `bug`, `reflection` | `api`, `test` |
| 3429 | `bug` | `validation` |
| 3695 | `bug`, `crash`, `incorrect-code` | `diagnostic` |
| 3706 | `correctness` | `diagnostic`, `fxc-disagrees`, `incorrect-code` |

No removals are proposed.

## Timeline safety check

Read-only timeline queries found pre-existing cross-reference counts of 3, 0, 0, 0 and 1 for
#2633, #3237, #3429, #3695 and #3706 respectively. Every event predates batch 009. **No
cross-reference was created by this triage branch.**

## Validation

- `python scripts/triage.py audit` exits 0: `no missing evidence in 45 issue(s)`.
- `python scripts/test_predicates.py` reports `all predicate tests passed`.
- `python scripts/render_comments.py 009` spliced all five current drafts, and
  `python scripts/render_overview.py` regenerated the 45-issue overview.
- The machine-path pattern was first proven against raw-backslash, JSON-escaped and
  forward-slash known positives (3/3 matched), then run across 311 issue/report artifacts.
  It found no leak outside the documented `data/issues/3237/method-notes.md` exception.
- `scripts/` is clean. `SKILL.md` remains modified by the orchestrator's existing changes;
  collation did not edit either location.

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


### Draft — [#2633](https://github.com/microsoft/DirectXShaderCompiler/issues/2633) [SPIRV][Question]Link libraries

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2633](https://github.com/microsoft/DirectXShaderCompiler/issues/2633).

Tested on `main` (`13730886e`) and on every release back to v1.5.2010. **Half of what
this issue asks for already works and has since v1.6.2104; the other half is still
absent.**

**Producing a library module works.** An `export` function gets SPIR-V linkage
decorations today:

```
dxc -T lib_6_3 -spirv -fspv-target-env=universal1.5 lib-export.hlsl
```
```
OpCapability Linkage
OpDecorate %foo LinkageAttributes "foo" Export
```

`-fspv-target-env=universal1.5` is required — under a Vulkan target env the same
compile stops at `Capability Linkage is not allowed by Vulkan 1.0 specification`,
which is expected for a module that is meant to be linked before a driver sees it.
This first appears in v1.6.2104 (v1.5.2010 does not emit it); PR #3234 looks to be
where it came in.

**Consuming one does not work.** Compiling the other side — @s-perron's example from
this thread, a declared-but-undefined `foo` — still fails on `main` and on all 19
releases from v1.5.2010 to v1.9.2607:

```
repro.hlsl:27:21: error: found undefined function
```

DXC rejects the unresolved call rather than emitting an `Import` decoration, so there
is nothing for `spirv-link` to resolve against. I found no user-code workaround:
`-default-linkage external` is DXIL-only; `dxc -link` rejects SPIR-V as
`Invalid DXIL container`; and the inline attributes split integer and string operands,
so neither can express `LinkageAttributes`.

**Clang's HLSL SPIR-V backend emits both decorations** for the same source without
`universal1.5`. It uses Itanium mangling (`_Z3fooDv4_f`) versus DXC's plain source name
(`foo`), so their modules would not currently resolve each other's symbols.

All five cases side by side: **https://godbolt.org/z/ca49jMrrc** (panes 1–2 export on
dxc, pane 3 import on dxc, panes 4–5 both on clang). Compiler Explorer is single-file,
so the two halves are `#ifdef`-selected in one source rather than separately compiled
and linked — it shows what each compiler emits, not a completed link.

The remaining design questions are the `Import` decoration, global variables, and
`lib_6_x` backwards compatibility, as @s-perron set out in
[this comment](https://github.com/microsoft/DirectXShaderCompiler/issues/2633#issuecomment-2253075613).
Triage does not decide them or imply an implementation commitment.

Suggested label: add `question` — the report is a question about a capability rather
than a defect, and `enhancement` alone does not distinguish the two. (`shader-linking`
looks apt by name but is used exclusively for DXIL linker bugs, so it would misroute
this.)

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3237](https://github.com/microsoft/DirectXShaderCompiler/issues/3237) Library Reflection : Listing parameters return E_FAIL

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3237](https://github.com/microsoft/DirectXShaderCompiler/issues/3237).

**Still reproduces on `main`** (`13730886e`; the local build reports
`1.9.0.5433`) and on all 21 releases I could measure, **v1.4.1907
(2019-07-15) through v1.9.2607 (2026-07-29)**.

`dxc.exe` cannot show this, so I drove the API directly. For
`export float3 Apply(float3 input)` compiled at `lib_6_3`:

```
ID3D12FunctionReflection::GetDesc -> 0x00000000 (S_OK)
  D3D12_FUNCTION_DESC.Name="\x01?Apply@@YA?AV?$vector@M$02@@V1@@Z"
  D3D12_FUNCTION_DESC.FunctionParameterCount=0
  D3D12_FUNCTION_DESC.HasReturn=FALSE
ID3D12FunctionParameterReflection::GetDesc(param 0) -> 0x80004005 (E_FAIL)
ID3D12FunctionParameterReflection::GetDesc(D3D_RETURN_PARAMETER_INDEX) -> 0x80004005 (E_FAIL)
```

That name is byte-for-byte the one @mrvux quoted in #657
(`^A?Apply@@YA?AV?$vector@M$02@@V1@@Z`, where `^A` is the leading `0x01`), so
the walk is landing where the report says. Note the two extra findings
alongside the `E_FAIL`: `FunctionParameterCount` is **0** for a function with
one parameter, and `HasReturn` is **FALSE** for one returning `float3`. DXC's
own `dxa -dumpreflection` agrees, so this is not an artefact of my harness —
with two parameters and a return value it still prints
`FunctionParameterCount: 0`, `HasReturn: FALSE`.

### It was never implemented, rather than broken

On `13730886e`:

1. `CFunctionReflection::GetFunctionParameter` (`lib/HLSL/DxilContainerReflection.cpp:2834`)
   ignores its index and always returns `&g_InvalidFunctionParameter`.
2. That object's `GetDesc` is `{ return E_FAIL; }` — unconditional (line 719).
3. `CFunctionReflection::GetDesc` carries `// Unset: INT FunctionParameterCount;`
   and `// Unset: BOOL HasReturn;` (lines 2904, 2906), which is why those read 0
   and FALSE — they are never written, not computed wrongly.
4. **`RuntimeDataFunctionInfo` in `RDAT_LibraryTypes.inl` has no parameter
   records at all** — no parameter list, types or return type. The data is not
   in the container, so this is an RDAT format addition, not a getter fix.

`git log -S GetFunctionParameter -- lib/HLSL/DxilContainerReflection.cpp` returns
exactly one commit, `c1b662784` (2018-04-11, "Support ID3DLibraryReflection").
The stub has never been edited. This matches what @tex3d wrote in #657: library
reflection here "was limited to known use cases that were needed for developers
using them at the time (for DXR)". @pow2clk's remark in the same thread — "I
notice we have no testing for it" — also still holds: `GetFunctionParameter`
has no caller anywhere in the repository, tests included.

### One note for anyone re-checking

The source in the issue body needs `export` to be reachable. Without it the
function has internal linkage and `D3D12_LIBRARY_DESC.FunctionCount` is **0**,
so the reported call is never reached — I confirmed that on all 21 releases,
including v1.5.2010, current when this was filed. That is a gap in the repro,
not in the report: with `export` added, it reproduces exactly as described.

Whether this is worth implementing remains the product question raised in
#657; these measurements do not address priority.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3429](https://github.com/microsoft/DirectXShaderCompiler/issues/3429) DXC Validation Error: TGSM pointers must originate from an unambiguous TGSM global variable

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3429](https://github.com/microsoft/DirectXShaderCompiler/issues/3429).

Still reproduces on `main` (dxc 1.9.0.5433, commit `ab5400907`, Debug), and on **all 20
bisectable release binaries measured from v1.4.1907 (2019-07) through v1.9.2607
(2026-07)**. The minimised repro from
[the 2024-04-28 comment](https://github.com/microsoft/DirectXShaderCompiler/issues/3429#issuecomment-2081259226)
still produces byte-identical output, on the same two source locations:

```
$ dxc -E main -T cs_6_0 repro.hlsl
error: validation errors

repro.hlsl:9:22: error: TGSM pointers must originate from an unambiguous TGSM global variable.
note: at '%13 = phi float addrspace(3)* [ %8, %7 ], [ %22, %11 ]' in block '#5' of function 'main'.
repro.hlsl:15:20: error: TGSM pointers must originate from an unambiguous TGSM global variable.
note: at '%15 = phi float addrspace(3)* [ %22, %19 ], [ %8, %10 ]' in block '#6' of function 'main'.
Validation failed.
```

Repro, with a `-Vd` pane showing the rejected module:
<https://godbolt.org/z/61Gb43GjM>

**The pointer is not ambiguous.** The same compile with `-Vd` succeeds, and every incoming
value of both phis is a GEP into the *same* global — the shader declares only one groupshared
array:

```llvm
%8  = getelementptr [6 x float], [6 x float] addrspace(3)* @"\01?thingies@@3PAMA", i32 0, i32 %1
%22 = getelementptr [6 x float], [6 x float] addrspace(3)* @"\01?thingies@@3PAMA", i32 0, i32 %17
%13 = phi float addrspace(3)* [ %8, %7 ], [ %22, %11 ]
```

In `lib/DxilValidation/DxilValidation.cpp` (~L3820-3849) the chain walk applies only when the
instruction is itself a GEP or a bitcast; anything else with a TGSM pointer result takes the
`else` branch and is rejected without its operands being examined. A `phi` therefore always
fails, however unambiguous its inputs. `dxv.exe` built from this tree rejects the module too,
so this is the in-tree validator and not only the redistributable `dxil.dll`.

`tools/clang/test/LitDXILValidation/GroupShared/tgsm-chained-gep-ambiguous.ll` shows the
rejection of `phi`/`select` is intentional — but every case it covers merges **two different**
globals, which is genuinely ambiguous. Whether the walk should accept a merge whose operands
all resolve to one global, or whether the optimizer should not form such a merge for TGSM, is
a design decision we are not making here.

Two smaller findings:

- **The `-Od` workaround costs all optimization, not just `-O3`.** On `main`, `-Od` and `-O0`
  compile clean; `-O1`, `-O2` and `-O3` all fail with the same rule. At `-O0` the GEP is simply
  repeated in each block and no `phi float addrspace(3)*` is ever formed — the pointer `phi` is
  created by optimization, from `-O1` upward.
- **v1.4.1907 reports the same rule without the `error:` prefix or source location**, instead
  printing `at 0x… inside block … of function main TGSM pointers must originate…`;
  [#2768](https://github.com/microsoft/DirectXShaderCompiler/issues/2768) preserves the same
  older wording.

`hlsl_clang_trunk` compiles this source without forming a merged groupshared pointer; it keeps
the address computation inside each branch (pane 4, checked against a control under the same
flags). Clang does not run the DXIL validator, so this describes its output, not what the rule
would accept.

Suggested label: add `validation` ("Related to validation or signing") alongside `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3695](https://github.com/microsoft/DirectXShaderCompiler/issues/3695) DXC Crash on Bad Shader

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3695](https://github.com/microsoft/DirectXShaderCompiler/issues/3695).

**Still reproduces.** The attached `shader.txt` crashes `main` at `1.9.0.5433` (`ab5400907`)
with the filed command line, and all 20 bisectable release binaries measured from v1.4.1907
to v1.9.2607.

Debug build, `dxc -T cs_6_0 -E main shader.txt` — exit `0xE0000001`, and this is the entire
output:

```
Internal compiler error: LLVM Assert
```

Under a debugger the assert is `assert(Val && "isa<> used on a null pointer")` at
`include/llvm/Support/Casting.h(96)`, reached from
`DxilLowerCreateHandleForLib::ReplaceResourceUserWithHandle`.

It is not Debug-only. Release v1.9.2607 exits `0xC0000005`:

```
Internal compiler error: access violation. Attempted to read from address 0x0000000000000019
```

All 20 measured releases crash. **v1.4.1907 and v1.5.2010 produce no output at all** — empty
stdout and stderr, exit `0xC0000005`.

### Smaller repro, and a correction

The body's guess that this is *"assigning one `RWTexture2D<float4>` global variable to another"*
turns out not to be the trigger. That construct on its own is diagnosed correctly:

```
error: local resource not guaranteed to map to unique global resource.
```

The 10-line crashing reduction passes a global resource through a function and assigns the
result back to **the same** global:

```hlsl
RWTexture2D<float4> A;

RWTexture2D<float4> pick(RWTexture2D<float4> tex) {
  tex[uint2(0, 0)] = 1.0;
  return tex;
}

[numthreads(8, 8, 1)]
void main(uint3 id : SV_DispatchThreadID) {
  RWTexture2D<float4> local = pick(A);
  A = local;
}
```

The straight assignment and the different-global function variant are diagnosed, not crashed.

### Compiler Explorer

<https://godbolt.org/z/aqPedMGE4> — `dxc_1_6_2112`, `dxc_trunk` and `hlsl_clang_trunk`, all at
`-T cs_6_0 -E main`. Both DXC panes exit 139 (SIGSEGV). CE runs Release Linux builds, so the
assert above cannot appear there.

Clang rejects the same source cleanly, with a location:

```
<source>:84:14: error: assignment to global resource variable '_blurResult' is not allowed
   84 |         _blurResult = filterFog;
<source>:35:21: note: variable '_blurResult' is declared here
```

(Checked against a control: a valid version of the same shader passes `hlsl_clang_trunk`
`-fsyntax-only` cleanly, so the error is specific to this construct.)

Suggested label: **`diagnostic`**, alongside the existing `bug`/`crash`/`incorrect-code` — the
defect is that invalid code produces no diagnostic, and #5681, #6016, #6964 and #7582 already
carry that combination.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3706](https://github.com/microsoft/DirectXShaderCompiler/issues/3706) Passing uninitialized var as index to structure buffer causes undef being passed in dxil

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3706](https://github.com/microsoft/DirectXShaderCompiler/issues/3706).

Still reproduces on `main` (1.9.0.5433, `ab5400907`) and in all 20 bisectable releases measured
from v1.4.1907 through v1.9.2607, including v1.6.2104, which shipped two days before filing.

Repro: https://godbolt.org/z/n9YeYKT3W

`dxc -T vs_6_2 -E main` on the shader as filed exits 0, emits no diagnostic, and produces the
reported line verbatim:

```llvm
%2 = call %dx.types.ResRet.i32 @dx.op.rawBufferLoad.i32(i32 139, %dx.types.Handle %1, i32 undef, i32 0, i8 1, i32 4)  ; RawBufferLoad(srv,index,elementOffset,mask,alignment)
```

The module passes DXIL validation and is signed.

**DXC already has the check — it is just not on by default:**

```
$ dxc -T vs_6_2 -E main repro.hlsl -Wall
repro.hlsl:10:19: warning: variable 'j' is uninitialized when used here [-Wuninitialized]
repro.hlsl:9:11: note: initialize the variable 'j' to silence this warning
```

`warn_uninit_var` is `DefaultIgnore` in `DiagnosticSemaKinds.td`; `-Wall` or
`-Wuninitialized` enables it. One caveat if that looks like the whole fix: it does
**not** fire on a partially-initialized index (`int2 j; j.x = 1;` then
`stbuf[j.y]`), which emits the same `undef` index and is silent even under `-Wall`.

Same source, other compilers:

| Compiler | Result |
| --- | --- |
| FXC (`/T vs_5_0`) | `error X4000: variable 'j' used without having been completely initialized` |
| DXC 1.6.2112 / trunk | exit 0, no diagnostic, `undef` index |
| Clang trunk (`-fsyntax-only`) | no diagnostic for `j` — it does warn on that same statement (`-Wsign-conversion`), so Sema reached the expression |

The validator rejects `undef` stored to a UAV (`Instr.UndefinedValueForUAVStore`), but
`RawBufferLoad` checks `elementOffset` and alignment, not the index. The slot matters: for a
ByteAddressBuffer, `elementOffset` on the same op must be `undef`
(`Instr.CoordinateCountForRawTypedBuf`).

The policy choice is among enabling the warning by default, adding a validator rule, or making
this a language-level error as FXC did. `microsoft/hlsl-specs#272` tracks the validator option
and cites this issue.

**Labels:** suggest adding `diagnostic` (the ask is a diagnostic, and one exists but is off),
`fxc-disagrees` (measured above) and `incorrect-code`. Not suggesting `validation` — it was
removed here deliberately in July 2024.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- **Sampling is strongly biased.** All five are open survivors filed between January 2020 and
  April 2021, deliberately mixed by subsystem rather than randomly selected. A batch of old
  open issues over-samples never-implemented capabilities and long-lived defects; five
  reproductions do not estimate the health of the backlog.
- #2633's release history starts nine months after filing because the older binaries have no
  SPIR-V CodeGen. The export transition is measured; its likely commit attribution is not
  proven by building that commit.
- #3237 measured 21 cached release DLLs, not every tag that exists. It required a custom
  harness and cannot be shown on Compiler Explorer.
- #3429's “always” means all 20 bisectable releases back to the 2019 floor. The non-bisectable
  v1.5.2003 tag was not needed to locate a boundary and was not probed.
- #3695's minimization establishes the tested straight-assignment and different-global
  controls; it does not prove no other trigger shape exists.
- #3706's runtime consequences were not tested. The evidence settles compiler output and
  diagnostics, not GPU behaviour.
- #3009's missing control artifact was identified but not backfilled; changing an earlier
  batch was outside scope.
- `reindex` was not run by explicit instruction. `audit` does not re-score, so method lessons
  discovered here were not applied retroactively.
- The absolute-path scan excludes `data/issues/3237/method-notes.md` only. That file
  deliberately quotes raw and JSON-escaped checkout-path spellings to document the escaping
  trap; changing them would destroy its evidence.
- The workspace remains deliberately dirty for orchestrator review. `SKILL.md` already had
  orchestrator edits; collation made no changes to it or to `scripts/`.

## Suggested next steps

1. Treat #2633 as a design/feature-routing decision and update the stale 2020 thread context
   if a maintainer agrees.
2. Decide whether #3237's existing API contract warrants implementation priority; its
   diagnosis and history are settled.
3. Keep #3429 and #3695 open with the proposed routing labels.
4. For #3706, decide between default warning policy, validator coverage and a language-level
   rule; link #3009 for discoverability without marking it duplicate.
5. Add an audit gate for machine-local paths and require any prose-claimed control to name its
   source and capture.
