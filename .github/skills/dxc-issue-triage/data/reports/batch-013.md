# DXC issue triage — batch 013

**Ground truth:** local Debug build, compiler-source-identical to upstream
[`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e6a9019e4e0823746470f3ab75341d6b)
(`1.9.0.5433`). The binary's fork-local build identifier appears only in
verbatim captured evidence; public citations use `13730886e`.

**Nothing was posted, edited, labelled or closed on GitHub. No DXC compiler
source was modified, and no commit or push was made.**

> [!IMPORTANT]
> **Sampling bias:** batches 011 onward are drawn exclusively from the oldest
> 100 open issues, at the user's request. The usual age mixing is deliberately
> suspended. Five issues in this batch advance that sweep to **61/100**.
> 5293 is a user-directed exception and is counted separately, alongside the
> four deliberately mixed recent issues 8527, 8725, 8732 and 8737.
>
> This batch is materially better balanced than batch 012: it exercises the
> crash path twice (3835 and 5293), plus debug information, reflection,
> preprocessing and a missing diagnostic. Its method findings therefore cover
> more than the enhancement-heavy previous batch.

## Immediate attention — 5293

> [!CAUTION]
> A new external report arrived on **2026-08-10** describing a Release crash
> and a Debug LLVM assert in production templated code. This issue was added
> by hand because a studio may be blocked now. Nothing from this triage was
> posted to the actively watched thread.

The reporter's exact `TRayVsAABB` paste is not the crashing function: it exits
0 because `out T2 intersections` is a vector and `isTrackedVar()` tracks only
scalar `out` parameters. Adding one scalar `out T` to the same function asserts
immediately. The draft leads with that distinction as search help, not as a
correction.

The underlying defect still reproduces. A Debug build asserts at
`CFGBlockValues::operator[]`; with `NDEBUG`, the valueless `Optional` feeds an
out-of-bounds `SmallBitVector` index. On the shipped v1.9.2607 binary the same
construct is latent at 28 tracked locals and access-violates at 29. That gives
the reporter a second evidence-backed explanation for “it was not crashing
before” that requires no compiler upgrade.

Release history is bounded carefully:

- v1.4.1907–v1.6.2106 reject `-HV 2021`: invalid probes, not clean results;
- v1.6.2112–v1.7.2212.1 predate the analysis under test;
- all 12 stable releases from v1.7.2308 through v1.9.2607 crash on the
  large-locals Release repro.

The v1.7.2308 boundary agrees independently with the
`-Wparameter-usage` presence control and source ancestry for `1380cf88e`.
Compiler Explorer shows v1.7.2212 clean, v1.7.2308 `SIGSEGV`, and trunk
`SIGSEGV`. PR 8401 is open, not merged; no fix or timeline is promised.

## Headline

- All six verdicts are **`repros`**, high confidence. There is no closure
  recommendation and therefore no blind close re-derivation requirement.
- Two tidy apparent regressions were false: 3535 crossed a reflection-metadata
  storage change, and 3872 crossed a disassembler-spelling change. Per-release
  self-tests exposed both.
- 3531, 3535 and 3863 share a useful boundary pattern: DXC produces relevant
  information internally, then loses or hides it before the public surface.
- 3835 and 5293 independently show why a Debug assert and a Release crash must
  be treated as possible faces of one defect.

| Issue | Repro | History | Recommendation | CE |
| --- | --- | --- | --- | --- |
| [3531](https://github.com/microsoft/DirectXShaderCompiler/issues/3531) | `repros` / partial | all 18 stable releases supporting SM 6.6 | keep open | [b11P9EvaG](https://godbolt.org/z/b11P9EvaG) |
| [3535](https://github.com/microsoft/DirectXShaderCompiler/issues/3535) | `repros` / partial | never exposed by reflection in 20 stable releases | enhancement, not a bug | [aYqW8oeWE](https://godbolt.org/z/aYqW8oeWE) |
| [3835](https://github.com/microsoft/DirectXShaderCompiler/issues/3835) | `repros` / complete | all 20 stable releases | keep open | [aYedzh96v](https://godbolt.org/z/aYedzh96v) |
| [3863](https://github.com/microsoft/DirectXShaderCompiler/issues/3863) | `repros` / prose-only | all 21 stable releases | keep open | n/a — measured single-file limitation |
| [3872](https://github.com/microsoft/DirectXShaderCompiler/issues/3872) | `repros` / agent-constructed | all 20 stable releases | keep open | [o8fEdbsMK](https://godbolt.org/z/o8fEdbsMK) |
| **[5293](https://github.com/microsoft/DirectXShaderCompiler/issues/5293) 🔔** | `repros` / complete | all 12 releases containing the faulty analysis | keep open | [MKsnrdq4T](https://godbolt.org/z/MKsnrdq4T) |

## Reindex

The mandatory first command ran before any shared-tool edit:

```text
reindexed 66 issue(s) and 1163 run(s)

evidence a completed triage should have left behind:
  3531, 3535, 3835, 3863, 3872, 5293: verdict.json has no reviewed_by
```

There were initially no changed scores, stale commands or failed declared
controls. The six reviewer gaps were expected collation work, not papered over;
all now record `gemini-3.1-pro-preview`.

After adding the missing HLSL-version classifier, reindex correctly moved four
archived 5293 captures:

```text
v1.4.1907: no-repro -> invalid-probe
v1.5.2010: no-repro -> invalid-probe
v1.6.2104: no-repro -> invalid-probe
v1.6.2106: no-repro -> invalid-probe
```

Each contains `dxc failed : Unknown HLSL version: 2021`, so none compiled the
repro. `reindex --accept` restamped only the derived verdict headers; captured
commands and output were untouched.

## Tooling repairs

Every behavioural repair in `scripts/triage.py` has a regression test,
including a negative control that would fail if the repair were removed.

### Multi-invocation `run --shader`

Retargeting now replaces HLSL sources while preserving source-less consumer
lines such as a later compile of generated `.i` or `.bc`. The command-list
wrapper still refuses a list containing no HLSL source at all.

Tests cover a preprocess-then-compile chain and the wholly source-less negative
case.

### `Unknown HLSL version`

The classifier now treats the fixed driver diagnostic as `invalid-probe`.
Tests cover the positive classification, an ordinary syntax-error negative
control, and the exception for an issue whose own positive predicate quotes
that diagnostic.

### Unrelated rejected options

`bisect` now warns when an unknown option, rather than the subject under test,
may be shortening history. The test pairs an unknown-option positive with an
invalid-profile negative. 3835 demonstrated the need: dropping an inert
`-Wno-parentheses-equality` after a byte-identity control extended its history
to v1.4.1907.

### Compiler Explorer evidence

- A multi-invocation `cmd.txt` now requires explicit per-pane arguments instead
  of silently linking line 1. Tests reject omitted overrides and accept a fully
  explicit set; the legacy two-value `ce_args()` return remains intact for
  issue-local scripts.
- A differing prior `manual-case-godbolt-verify.txt` is archived by content
  hash before replacement. Tests cover first write, differing write and an
  identical rerun that must not create a duplicate.
- On Windows, `-Fc -` is rejected because dxc creates a literal file named
  `-`; tests reject that spelling on Windows while accepting a real output
  filename and preserving the CE/Linux convention.

### Database findings

The reported `triage.py sql` failure on
`cached_path IS NOT NULL AS cached` could not be reproduced: the exact query
works. No speculative parser change was made.

The separate schema finding was real: `releases` has no `seed_local` column.
`SKILL.md` now says that the importer stores either downloaded or seeded
executables in `cached_path`.

## Method changes

`SKILL.md` now records the batch's durable lessons:

- a predicate reads the instrument as well as behaviour; evaluate self-tests
  per release and use a portable twin or fixed reader when the instrument
  changes;
- with `-Zi`, anchor a missing identifier on its metadata form, use embedded
  source as an anti-vacuity control, and keep self-test variables live;
- probe the earliest stage that should contain a missing artifact (`-fcgl`
  localised 3531 to DXIL lowering);
- try `dxa -dumpreflection` first, read what its dumper omits, and vary release
  DLLs behind a fixed reflection reader;
- a subsystem-presence control is required when old compilers accept the
  syntax but predate the code under test;
- multi-command shader retargeting preserves generated-artifact consumers;
- an unrelated rejected option can silently shorten history;
- Windows `-Fc -`, multi-invocation CE links, CE evidence preservation and
  same-file `-D` controls are documented;
- a to-do label such as `check-in-clang` should not be proposed after the work
  is complete;
- a neighbouring issue's measurements may be inherited, but its source
  explanation remains a hypothesis until re-measured;
- the rendered warning callout is the only draft marker; all batch drafts now
  omit invisible HTML draft comments.

## Cross-batch correction and duplicate checks

### 3863 versus 3044

They are related, not duplicates. 3044 needs a new option and plumbing that
changes the preprocessed file. 3863's option is already parsed, its trace is
already captured, and the missing behaviour is console output only.

3863 also falsified 3044's method-note claim that `-H` could not run under
`-P`. Direct `IDxcCompiler3::Compile` measurement found 86 bytes in
`DXC_OUT_REMARKS`, empty without `-H`; only `DxcContext::Preprocess()` fails to
print it. 3044's `method-notes.md` is corrected in place. Its draft comment
never repeated the false claim, and `SKILL.md` did not contain it.

### 3535 versus 2952

They are consistent, not duplicates. 2952 asks to expose data already present
in RDAT. 3535's input-struct member names are discarded during lowering, so a
fix needs preservation and then an API route.

### Wider corpus pattern

Across the 66 indexed issues, 2952 and 3044 are adjacent “internal information
not exposed” cases, while this batch sharpens the distinctions:

- 3531: debug metadata exists before lowering and is dropped;
- 3535: field-name/semantic annotations exist before lowering and are dropped;
- 3863: include-trace text reaches `DXC_OUT_REMARKS` and is not printed.

The shared boundary pattern is useful for routing, but the fixes remain
different and none of these issues should be collapsed into a duplicate.

## Independent draft review

The required review ran on `gemini-3.1-pro-preview`, a different model from
every draft author. It read all six current drafts and their evidence, with
concision as the primary criterion and exact technical evidence off-limits.

Applied selectively:

- 3531: removed a redundant release count while retaining the exact range and
  the two invalid-profile results.
- 3835: removed a rhetorical restatement that the explicit range already
  proved.
- 3863: removed a redundant “either”.
- 3872: removed a redundant `always-repro'd`/“no window” restatement while
  retaining the 20-release range and source history.

Rejected after checking the evidence:

- cuts to per-release absence controls in 3531, API-reader details in 3535,
  exact rejected-option and REMARKS controls in 3863, and the validator control
  in 3872: these are load-bearing falsification evidence, not exposition;
- replacements that traded exact release counts or diagnostics for “all
  tested releases”: less precise, with no meaningful saving;
- every proposed 5293 cut that weakened scope. Replacing “local Debug build”
  with “main” erased the Debug/Release distinction; collapsing the release
  table removed both invalid-probe classes and independent boundary checks;
  deleting the scope section would imply the actual Asobo or Frostbite shaders
  were reproduced when only the mechanism and constructed Release trigger
  were.

Every batch verdict has a non-empty reviewer distinct from its author.

## Per-issue findings

### 3531 — local resource debug metadata is lost during lowering

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`still-valid-keep-open`.

The repaired public snippet reproduces on every stable release supporting SM
6.6. The local resource gets no variable entry, while a global heap resource
and an ordinary local in the same run do. A one-token `uint` control proves
each probe's reader can name that exact local. The gap also affects a local
alias of a bound resource. `-fcgl` carries the variable and
`llvm.dbg.declare`, proving the loss occurs later in DXIL lowering.

### 3535 — input-struct field names require preserve-then-expose

**Confirmed verdict:** `repros`, high confidence, `enhancement-not-bug`.

No reflection call can reach an `ID3D12ShaderReflectionType` from a signature
parameter, and the non-debug container no longer contains the input struct to
annotate. The field-name/semantic pair exists at `-fcgl`. A fixed
`dxa -dumpreflection` reader driving each release's `dxcompiler.dll` reports
no names in all 20 stable releases. The apparent v1.5.2010 regression was only
reflection metadata moving from DXIL to `STAT`.

### 3835 — CodeGen crash plus silent wrong code

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`still-valid-keep-open`.

An incomplete array type reaches clang CodeGen uncompleted. Debug asserts;
stepping past the assert reaches the reported Release access violation. The
minimal Release case instead emits an empty entry point on all 20 releases,
and a compute restatement exposes `undef` UAV stores that DXC's validator
rejects. FXC handles the construct; Clang diagnoses it. Despite the title, the
fault is not DXIL validation.

### 3863 — include trace is produced and then dropped

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`still-valid-keep-open`.

All 21 stable releases accept `-H`/`-Vi` under `-P`, print no trace and produce
byte-identical `.i` output. The library already returns the trace in
`DXC_OUT_REMARKS`; `DxcContext::Preprocess()` alone does not print it.
`-M` provides a compile-mode dependency list from v1.7.2207 but still does not
compose with `-P`. A CE skip is recorded because single-file panes cannot show
either the include-trace presence control or the missing trace.

### 3872 — four invalid signature cells remain accepted

**Confirmed verdict:** `repros`, `always-repro'd`, high confidence,
`still-valid-keep-open`.

The four reported `SigPoint` cells still accept and lower
`SV_ShadingRate`; the VRS specification rules out DS by name. Same-stage `NA`
controls prove diagnostics are reachable. Standalone `dxv` accepts the output
because front end and validator consult the same generated interpretation
table. The initial v1.5.2010 boundary was a `NONE`/`SHDINGRATE` disassembler
spelling change; a portable predicate confirms all 20 releases reproduce.

### 5293 — scalar template `out` analysis crashes

**Confirmed verdict:** `repros`, high confidence, `still-valid-keep-open`.

See the highlighted section above. The issue also carries `text_stale`: the
standing claim that removing the assert has no code-generation impact is
contradicted by the measured out-of-bounds path and 12 shipping Release
crashes.

## Timeline integrity

Read-only timeline checks found no cross-reference events on 3531, 3535, 3835,
3863 or 3872. 5293 has two pre-existing events (2023-06-14 and 2026-04-23);
both predate this batch. No branch-created cross-reference was added.

## Verification

- Final reindex: **66 issues / 1163 runs**; every probe re-scores as captured,
  none are stale, and no issue is missing required evidence.
- Predicate/tool regression suite: **186 passed / 0 failed**.
- `triage.py audit`: **66 issues**, no missing evidence.
- `check_paths.py`: **3056 committable text files**, 16 documented matches in
  four allowlisted files, zero unexpected machine paths.
- Generated-report stability: re-running both renderers changed neither
  `batch-013.md` nor `overview.md`.
- Reviewer audit: **6/6** batch verdicts reviewed, zero missing and zero
  self-reviews.
- Public-citation audit: zero links targeting the fork-local SHA.
- Git status: **338** changed or untracked paths, all under this skill;
  `git add -An` reports the same 338 candidates. The index contains zero
  staged paths, and the candidate set contains zero binary extensions and zero
  NUL-bearing files.
- Timeline checks found only the two pre-existing 5293 cross-references named
  above. GitHub access remained read-only.

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


### Draft — [#3531](https://github.com/microsoft/DirectXShaderCompiler/issues/3531) No debug info for locally-declared dynamic resources (SM 6.6)

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3531](https://github.com/microsoft/DirectXShaderCompiler/issues/3531).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on every stable release that can
compile the repro: v1.6.2104 through v1.9.2607. v1.4.1907 and v1.5.2010 answer
`error: invalid profile cs_6_6`, so SM 6.6 predates them.

The snippet needs one repair to compile — `floatRWUAV` is never declared; I added
`RWBuffer<float> floatRWUAV : register(u0);` and changed nothing else. Built with
`-T cs_6_6 -E DynamicResources -Zi -Qembed_debug`, the DXIL carries three debug-variable
entries:

```llvm
!11 = !DIGlobalVariable(name: "DynamicBuffer", scope: !0, file: !1, line: 10, type: !12, isLocal: true, isDefinition: true)
!13 = !DIGlobalVariable(name: "floatRWUAV", linkageName: "\01?floatRWUAV@@3V?$RWBuffer@M@@A", scope: !0, file: !1, line: 8, type: !14, isLocal: false, isDefinition: true)
!42 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "val", scope: !7, file: !1, line: 14, type: !43)
```

and none for `DynamicallyIndexedDynamicBuffer`. Its `createHandleFromHeap` does keep a source
location (`!dbg ... line:15 col:59`), so what is missing is the variable entry rather than
every trace of the declaration.

Two things the triage adds to the report:

- **It is not specific to dynamic resources.** The same shader with the local aliasing a bound
  `RWByteAddressBuffer : register(u1)` also gets no `!DILocalVariable`. Dynamic resources are
  where it bites, because there is no binding for a tool to fall back on.
- **The front end emits it and DXIL lowering drops it.** At `-fcgl` both the variable and its
  declare are present:
  `!55 = !DILocalVariable(tag: DW_TAG_auto_variable, name: "DynamicallyIndexedDynamicBuffer", scope: !7, file: !1, line: 15, type: !12)`.
  `-Od` shows the same three entries and the same absence, so it is not an optimisation
  artefact.

Control for the absence: changing that local's type to `uint` and nothing else makes
`!DILocalVariable(... name: "DynamicallyIndexedDynamicBuffer" ... line: 15)` appear — on main
and on all 18 releases that compile the repro. So each of those compilers could name the
variable and did not.

[Compiler Explorer](https://godbolt.org/z/b11P9EvaG) — dxc 1.6.2112 and trunk, same result.
Note that Compiler Explorer appends `-Zi -Qembed_debug -Fc -` to every DXC pane; here that
matches the flags used locally, and the banner shifts pane line numbers relative to the ones
quoted above.

Label suggestion: add `debug info`; `bug` still fits.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3535](https://github.com/microsoft/DirectXShaderCompiler/issues/3535) Retrieving reflection data for structs used in input signatures

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3535](https://github.com/microsoft/DirectXShaderCompiler/issues/3535).

Still accurate on `main` (1.9.0.5433, `13730886e`): there is no way to get
`mPos` / `mColor` from reflection, and the reason is stronger than "no API for
it" — the names are never emitted, so there is nothing an API could return.

**Why no call can reach them.** `ID3D12ShaderReflectionType` is the only
interface that names struct members, and the only methods on
`ID3D12ShaderReflection` that lead to one are `GetConstantBufferByIndex`,
`GetConstantBufferByName` and `GetVariableByName`. Nothing takes a signature
parameter index and returns a type. So @aclysma's observation is right about
the method — `CShaderReflectionType::GetMemberTypeName` does return the member
name, from `fieldAnnotation.GetFieldName()`
([DxilContainerReflection.cpp:796](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/DxilContainerReflection.cpp#L796),
[:1318](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/DxilContainerReflection.cpp#L1318)) — but it
can only be reached through a constant buffer or a named variable, so it
cannot be called for `VertexIn`. (It is probably also not a bug:
`DxilContainerTest.cpp` compiles the same shader with `d3dcompiler` and
asserts DXC returns the identical string, so it matches FXC.)

**Why the data is not there either.** Compiling your shader with a constant
buffer added alongside it, `-Qkeep_reflect_in_dxil` shows the reflection type
table naming the cbuffer struct's fields (tag 6 is the field-name tag):

```
!dx.typeAnnotations = !{!7, !13}
!7 = !{i32 0, %struct.CbStruct undef, !8, %Params undef, !11}
!9 = !{i32 6, !"cbAlpha", i32 3, i32 0, i32 7, i32 9}
```

There is no matching entry for `VertexIn`, and `%struct.VertexIn` is not in
the module's type list at all — entry-point struct parameters are scalarised
into signature elements during lowering, so nothing survives to annotate. The
input signature is metadata keyed by semantic:

```
!11 = !{i32 0, !"POSITION", i8 9, i8 0, !12, i8 0, i32 1, i8 3, i32 0, i8 0, !13}
```

The mapping you want does exist earlier: at `-fcgl`, before lowering, one
annotation carries both halves —

```
!14 = !{i32 6, !"mPos", i32 3, i32 0, i32 4, !"POSITION", i32 7, i32 9}
```

So supporting this is two pieces of work — preserve the annotation through
lowering, then design a way to expose it — not a descriptor field addition.

**This is not new.** Driving `ID3D12ShaderReflection` (via `dxa
-dumpreflection`) against every stable release from v1.4.1907 to v1.9.2607,
with each release's own `dxcompiler.dll`, no release reports the member names.
Nothing regressed.

**A workaround, if you control the compile.** `-Zi` keeps the names in debug
info:

```
!32 = !DICompositeType(tag: DW_TAG_structure_type, name: "VertexIn", ...)
!34 = !DIDerivedType(tag: DW_TAG_member, name: "mPos", scope: !32, file: !1, line: 32, baseType: !24, size: 96, align: 32)
```

Not reflection, and not something you would ship, but a code generator that
runs its own compile step can read it.

[Compiler Explorer](https://godbolt.org/z/aYqW8oeWE) — DXC 1.6.2112, DXC
trunk, and FXC. Look at the input-signature tables (semantics only) against
the buffer-definitions blocks (member names), in **both** compilers. Note that
CE appends `-Zi -Qembed_debug`, so the DXC panes contain `mPos` in debug
metadata and embedded source, and FXC's `// Initial variable locations:`
comment names `vin.mPos` too — none of that is reflection.

Suggested labels: `reflection`, `enhancement`, `api`. Whether to preserve and
expose parameter member names is a design decision for the reflection API, not
something this triage can settle.
[#2952](https://github.com/microsoft/DirectXShaderCompiler/issues/2952) asks
for a different missing piece of reflection data and may be worth tracking
alongside.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3835](https://github.com/microsoft/DirectXShaderCompiler/issues/3835) Internal compiler error on shader validation

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3835](https://github.com/microsoft/DirectXShaderCompiler/issues/3835).

**Still reproduces on `main` (1.9.0.5433, `13730886e`)**, and on every stable release from
**v1.4.1907 (2019-07) through v1.9.2607** — 20/20, linear sweep, no fix window.

Compiler Explorer, the shader exactly as filed: <https://godbolt.org/z/aYedzh96v>

The trigger is the incomplete array type in these two declarations:

```hlsl
float _expr13[] = perVertexStruct.gl_ClipDistance;
float _expr14[] = perVertexStruct.gl_CullDistance;
```

Give either an explicit bound and the shader compiles cleanly.

### The title is misleading

This is not a DXIL validation problem. DXC crashes in clang CodeGen, before there is any DXIL to
validate. An assert-enabled build stops at the assert tex3d identified:

```
Error: assert(!isIncompleteType() && "This doesn't make sense for incomplete types")
dxcompiler!clang::Type::isConstantSizeType
dxcompiler!clang::CodeGen::CodeGenFunction::EmitAutoVarAlloca
```

A release build has that assert compiled out and runs on into a null dereference — the reported
symptom. Running the debug binary with asserts stepped over reaches it in the same process, on
the same input, so these are demonstrably one defect and not two:

```
Access violation - code c0000005
dxcompiler!ConvertScalarOrVector
dxcompiler!AddMissingCastOpsInInitList
dxcompiler!CGMSHLSLRuntime::EmitHLSLInitListExpr
```

### The silent half is arguably worse than the crash

tex3d's 5-line repro doesn't crash a release build — it **compiles successfully and emits an
empty entry point** on all 20 releases. No load, no `storeOutput`, no diagnostic. Adding `[1]`
to the declaration produces correct code on every one of them.

Restated as a compute shader so the bad value reaches a UAV, `dxc_trunk` shows what actually
happened:

```
error: validation errors
error: Assignment of undefined values to UAV.
note: at 'call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 0, i32 undef, i32 undef, i32 undef, i32 undef, i32 undef, i8 15)'
```

The front end produced `undef` for every component. The validator is doing its job here; it is
catching DXC's own output.

### Both other compilers have already picked an answer, and they differ

- **FXC compiles the filed shader** (`/T vs_5_0 /E vert_main`, exit 0), confirming llvm-beanz's
  comment. On the reduced case its output is byte-identical to the explicitly-sized version
  (`store_uav_typed u0.xyzw, l(0,0,0,0), l(7,7,7,7)`) — it handles the form correctly, not just
  tolerantly.
- **Clang's HLSL front end rejects it**: `error: array initializer must be an initializer list`,
  on exactly those two lines (third pane in the link — its `SV_ClipDistance` errors are an
  unrelated gap). Controlled against a trivial shader and against the one-token sized variant,
  both of which compile clean.

So the language question tex3d raised is still open in DXC while the successor has already
chosen "diagnose and fail" and FXC has chosen "support it". That decision isn't triage's to
make, but whichever way it goes, crashing on one input and silently emitting an empty entry
point on another isn't a defensible outcome for either.

### Labels

Keep `bug`, `crash`, `incorrect-code` — all three are independently evidenced. Suggest adding
**`correctness`** (the silent empty entry point and the `undef` stores are wrong code, separate
from mishandling invalid input) and **`fxc-disagrees`** (measured above). Possibly
**`hlsl-next`**, since the open question is a language one. Not `validation`, despite the title:
the fault is in CodeGen.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
````

### Draft — [#3863](https://github.com/microsoft/DirectXShaderCompiler/issues/3863) Support -H and -P at the same time

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3863](https://github.com/microsoft/DirectXShaderCompiler/issues/3863).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on **all 21 stable
releases from v1.4.1907 to v1.9.2607** — every one of them accepted `-H` under
`-P`, and none of them printed anything.

```
$ dxc -T ps_6_0 -E main -H control-compile.hlsl
; Opening file [./inc-comp-a.h], stack top [0]
; Opening file [./inc-comp-b.h], stack top [1]

$ dxc -P repro.hlsl -Fi preprocessed.i -H
[exit] 0
--- stdout ---

--- stderr ---
```

`-H` is parsed, not swallowed: an unknown dash-flag in the same position exits 1
with `dxc failed : Unknown argument: '-ZZZNONSENSE3863'`. It is also completely
inert — the preprocessed output is byte-identical (SHA-256) with `-H`, with
`-Vi`, and with neither.

**The trace is not missing; it is dropped.** `EnableDisplayIncludeProcess()`
runs before the `isPreprocessing` branch
([dxcompilerobj.cpp#L674](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/tools/clang/tools/dxcompiler/dxcompilerobj.cpp#L674)),
and the common tail stores stdout into `DXC_OUT_REMARKS` for both paths.
Driving `IDxcCompiler3::Compile` directly with `-P -Fi out.i -H` confirms it —
the API already returns exactly what this issue asks for:

```
IDxcResult::GetOutput(DXC_OUT_REMARKS) ->
Opening file [./inc-pp-a.h], stack top [0]
Opening file [./inc-pp-b.h], stack top [1]
```

(controls: without `-H` that output is empty; on a normal compile it is
present.) `DxcContext::Compile()` prints it —
[dxc.cpp#L918](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/tools/clang/tools/dxclib/dxc.cpp#L918)
— while `DxcContext::Preprocess()`
([dxc.cpp#L1005](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/tools/clang/tools/dxclib/dxc.cpp#L1005))
never asks for it. The combination is not diagnosed and is absent from the
"compiler options ignored with Preprocess" warning list
([HLSLOptions.cpp#L980](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/DxcSupport/HLSLOptions.cpp#L980)),
so this looks unimplemented rather than deliberately rejected.

Since 2021 the dependency-listing flags referenced in the 2021-11-18 comment
did land: `-M` prints the include list from **v1.7.2207** onward, and composes
with `-H`. It is a compile mode, though — it needs `-T`, and it does not
combine with `-P`.

```
$ dxc -T ps_6_0 -E main -M -H repro.hlsl
repro.hlsl: repro.hlsl \
 inc-pp-a.h \
 inc-pp-b.h

; Opening file [./inc-pp-a.h], stack top [0]
; Opening file [./inc-pp-b.h], stack top [1]
```

Suggested labels: **`usability`** (today's alternative is a full compile you did
not want) and **`low-hanging-fruit`** — the data is already produced and already
returned by the library, so the remaining work is confined to the `dxc.exe`
preprocess path. Whether to do it is a maintainer call.

No Compiler Explorer link: the symptom is a *missing* include trace, a CE pane
is single-source, and with no header to open `-H` prints nothing there even on a
normal compile — so a pane could show neither the symptom nor the working case.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3872](https://github.com/microsoft/DirectXShaderCompiler/issues/3872) SV_ShadingRate allowed in certain shader signatures where it shouldn't be allowed

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3872](https://github.com/microsoft/DirectXShaderCompiler/issues/3872).

Still reproduces, and has since the semantic shipped. Checked against `main` at `13730886e`
(a local Debug build reporting `1.9.0.5433`; it self-reports a different, fork-local hash) and
against all 20 stable releases from `v1.4.1907` to `v1.9.2607`. The four cells you named have
carried `SV _64` since `ecb4e3b4b` added the
semantic in 2018, so this is original behaviour rather than a regression.

All four positions compile clean today, and the semantic is lowered as a real system value —
not quietly demoted to arbitrary:

```
$ dxc -T ds_6_4 -E DSOutMain repro.hlsl
[exit] 0
; Output signature:
; Name                 Index   Mask Register SysValue  Format   Used
; SV_ShadingRate           0   x           1SHDINGRATE    uint   x
```

Same for `HSCPIn`, `HSCPOut` and `DSCPIn`. The VRS spec sentence backs the report: *"Setting
SV_ShadingRate is permitted from VS, GS or MS stages. It is not permitted from other stages, for
example DS."* `DSOut` is named outright there.

**The silence is a table decision, not a missing check.** Moving the same semantic into cells the
same table already marks `NA`, in the same stages and on the same command lines, produces
diagnostics immediately:

```
error: Semantic SV_ShadingRate is invalid for shader model: hs   # PCOut
error: Semantic SV_ShadingRate is invalid for shader model: ds   # DSIn
```

so `HLSignatureLower`'s `NA` arm is reached in both stages and just isn't asked to fire.

**Validation doesn't catch it either, and structurally can't.** `dxv` accepts all four containers
(control: a shader with a root signature that doesn't cover its SRV is rejected in `vs`, `hs` and
`ds` through the identical two steps). That's expected once you look at why:
`ValidationRule::SmSemantic` resolves through `SigPoint::GetInterpretation`
(`DxilValidation.cpp:5032`) — the same table the front end reads. One table, both gates. Good
news for the fix, which is a single-line change, but it does mean there's no second line of
defence here; flagging it since the issue is labelled `validation`.

**Where the fix goes:** the `.inl` is generated (`hctdb_instrhelp.get_interpretation_table()`), so
the edit is the `ShadingRate` CSV row in `utils/hct/hctdb.py:8019`. `docs/DXIL.rst` and
`SystemValueTest.cpp` both follow the table rather than restating it; new FileCheck coverage in
the style of `shadingrate3.hlsl` would be the manual part. Worth noting it's a source-breaking
change for anyone who has such a shader compiling today, so it probably wants a release note.

**On the `GSVIn` question you left open** — still accepted (`gs_6_4` puts it in the per-vertex
input signature). The spec sentence above is about *setting* the rate and doesn't say whether a GS
may *read* a per-vertex rate from the VS, so that one still looks like it needs an answer rather
than a code change.

**Re. the 2024 note about the semantic work in clang:** clang trunk doesn't model this semantic at
all yet — `error: unknown HLSL semantic 'SV_ShadingRate'` (controlled by an A/B on the same file
with the declaration `#ifdef`'d out, which compiles clean). So these four cells are still an open
input to that work, not something already inherited. FXC rejects it too, but rejects it in the
*vertex* shader as well — it predates SM 6.4 — so it isn't evidence either way.

Compiler Explorer, with the controls in the same file:
**https://godbolt.org/z/o8fEdbsMK** — panes 1 and 3 are accepted (`ds_6_4 DSOutMain`,
`hs_6_4 HSCPInMain`), panes 2 and 4 are the same compiler and stage diagnosing the `NA`
neighbour, pane 5 is `dxc_1_6_2112` giving the same answer as trunk.

Suggested labels: keep `validation`, add `diagnostic` and `incorrect-code` — the observable
defect is a missing diagnostic on code that should be rejected, even though the fix lands in the
table validation shares.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#5293](https://github.com/microsoft/DirectXShaderCompiler/issues/5293) Assert in `template` + `out` functions when it has local variables

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5293](https://github.com/microsoft/DirectXShaderCompiler/issues/5293).

@rbertin-aso — the exact `TRayVsAABB` function you pasted compiles cleanly here
(exit 0), which helps narrow the search. Its `out T2 intersections` is a vector,
and this analysis tracks only scalar `out` parameters. Adding one scalar
`out T` to that same function asserts immediately. The function triggering the
crash in your shaders is therefore likely another template with a scalar
`out` (`float`, `uint`, `bool`, ...) and at least one local.

**The issue itself still reproduces.** Confirmed on a local **Debug** build of
`13730886e` (1.9.0.5433), and the underlying defect is present in every shipped
release from **v1.7.2308 through v1.9.2607**. A second trigger may explain “it
was not crashing before” without a compiler change: crossing from 28 to 29
tracked locals turns the latent out-of-bounds access into a Release crash.

### Why this looked "harmless" for so long

Running the description's example against all 20 catalogued releases gives exit 0 every time.
That is not a fix — every release is a **Release** build, so the assert is compiled out, and
that example is small enough to survive the aftermath.

@simontaylor81 wrote in May 2024 that with the assert gone the valueless `Optional` is read
anyway and used to index a vector out of bounds. That is measurable, and it is what happens:

```
Optional::getValue          assert(hasVal)
Optional::getPointer
SmallBitVector::operator[]  "Out-of-bounds Bit access."
SmallBitVector::set         "undefined behavior"
```

`scratch` is `PackedVector<Value, 2, SmallBitVector>`, and `SmallBitVector` keeps its bits
inline only while they fit in `SmallNumDataBits = 57` — that is **28** two-bit entries. Past
that it heap-allocates, and the out-of-bounds index stops being a harmless masked shift and
becomes a wild pointer dereference.

So the number of local variables in the function decides which symptom you get. Taking the
description's example and varying only that, on the **shipped v1.9.2607 release binary**:

| locals | exit |
| --- | --- |
| 27 | `0x00000000` |
| 28 | `0x00000000` |
| **29** | **`0xC0000005`** (access violation) |
| 30, 32, 40, 64, 120 | `0xC0000005` |

Same binary, same construct — one shader compiles, the next crashes. Controls on that same
binary: removing the template, or changing `out` to `inout`, gives exit 0 in every case, so
this is this defect and not "a big function".

**This may be why it "was not crashing before" without any compiler upgrade on your side:**
adding a couple of locals to an already-affected templated function is enough to cross that
threshold. The bug is latent well before it becomes visible.

### Which releases are affected

| releases | behaviour |
| --- | --- |
| v1.4.1907 – v1.6.2106 | cannot compile the repro at all (no `-HV 2021`) — no evidence either way |
| v1.6.2112 – v1.7.2212.1 | clean, because the analysis containing the defect does not exist yet |
| **v1.7.2308 – v1.9.2607** | **crash (`0xC0000005`), all 12 releases** |

The boundary is `1380cf88e` ("Add diagnostics for uninitialized `out` parameters", #5047),
first shipped in v1.7.2308. Two independent checks agree on it: whether the release emits
`-Wparameter-usage` at all, and `git merge-base --is-ancestor`.

Reproduced on Compiler Explorer, which runs **Release** builds — so it speaks to the
configuration you are shipping: <https://godbolt.org/z/MKsnrdq4T>

```
dxc 1.7.2212   exit 0
dxc 1.7.2308   SIGSEGV
dxc trunk      SIGSEGV
```

The workarounds from the description still hold, all three verified here: drop the template,
use `inout` instead of `out`, or have no locals in the function. `inout` is usually the
smallest change.

### Root cause

`DeclToIndex::computeMap()` builds its index from the DeclContext's declarations. For a
**function-template instantiation** the `out` parameter is not among them, so the lookup for
the assignment returns an empty `Optional` —
`tools/clang/lib/Analysis/UninitializedValues.cpp:232`, reached via
`Sema::InstantiateFunctionDefinition` → `AnalysisBasedWarnings::IssueWarnings` →
`runUninitializedVariablesAnalysis`. That single fact accounts for all three workarounds.

PR #8401 appears to target this and is open, not merged, as of writing.

### Scope of this testing

The assert was observed on a local **Debug** build; the crash figures come from the shipped
**Release** binaries and from Compiler Explorer, which is also Release. The large-locals
shader used to expose the Release crash is one I constructed to make the symptom
deterministic — it is not anyone's reported code. I have not tried to reproduce the specific
crash in the Asobo or Frostbite shaders themselves, only to establish the mechanism and the
affected range.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- No issue was posted to, edited, relabelled, closed or reopened.
- Compiler Explorer uses Release builds; Debug-only assertions are represented
  only by the local Debug captures, while CE corroborates Release crashes.
- 3863 has no CE link because the working presence control itself requires a
  second source file.
- The large-locals 5293 shader is constructed to expose the Release failure.
  The specific Asobo and Frostbite production shaders were not reproduced.
- Stable release history excludes prereleases unless an issue explicitly names
  one and opts in. None in this batch did.
