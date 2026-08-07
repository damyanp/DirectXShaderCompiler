# DXC issue triage — batch 010

**Ground truth:** local Debug build source-identical to upstream `main` at
`13730886e6a9019e4e0823746470f3ab75341d6b` (`1.9.0.5433`). The binary's
verbatim `--version` string contains `ab5400907`; that fork-local merge was
orphaned by a history rewrite and is evidence only, not a source citation.

**Nothing was posted, labelled, closed, committed or pushed. No DXC compiler
source was modified.**

## Headline

- **#3811 has changed behavior and stale text:** the exact filed shader has
  warned since v1.7.2308, while the validator's PHI-carried `undef` gap remains.
- **#3726 has a reader trap:** applying the standing suggestion to make the
  resources `static` makes the DXIL path compile cleanly, but the as-filed
  bound-global form still reaches the back-end error and remains silent in Sema.
- #2604 is a longstanding API enhancement, not a compiler regression.
- #3686 remains a publication-policy question: no macOS assets among 26
  published releases; Linux assets have shipped since v1.7.2212.
- #3708 remains the documented FXC/DXC constant-expression language gap.

## Summary

| # | Title | Status | History | Suggested action | Compiler Explorer |
| --- | --- | --- | --- | --- | --- |
| [#2604](https://github.com/microsoft/DirectXShaderCompiler/issues/2604) | Support `-Fc` through the compiler API | **repros** | 21 measured release DLLs plus `main` | enhancement, not bug | n/a — direct API harness |
| [#3686](https://github.com/microsoft/DirectXShaderCompiler/issues/3686) | Publish macOS release binaries | **not-compiler-verifiable** | 0 macOS assets in 26 published releases / 73 assets | needs human judgement | n/a — release census |
| [#3708](https://github.com/microsoft/DirectXShaderCompiler/issues/3708) | Component access not a constant expression | **repros** | all 20 measured releases | keep open | [51xjeKra5](https://godbolt.org/z/51xjeKra5) |
| [#3726](https://github.com/microsoft/DirectXShaderCompiler/issues/3726) | Sema should not allow assignment to resource | **repros** | DXIL error in 20 releases; Sema silent wherever measured | keep open | [77EjzsnP9](https://godbolt.org/z/77EjzsnP9) |
| [#3811](https://github.com/microsoft/DirectXShaderCompiler/issues/3811) | Uninitialized dynamic-loop value reaches `undef` ⚠️ | **changed-behavior** | validator gap in all 20 releases; warning from v1.7.2308 | keep open | [57zn3j6YK](https://godbolt.org/z/57zn3j6YK) |

Confidence is `high` on all five.

## Per-issue findings

### #2604 — API/driver split, unchanged

Both `IDxcCompiler::Compile` and `IDxcCompiler3::Compile` return a result with
`E_INVALIDARG` for `-Fc`; `-Qunused-arguments` turns this into a successful
compile that silently ignores the option. No file and no
`DXC_OUT_DISASSEMBLY` are produced. The same DLL through `dxc.exe` writes the
listing, and `IDxcCompiler::Disassemble` returns it separately. This is unchanged
on `main` and all 21 measured release DLLs. Merely marking `-Fc` as a core
option would suppress the error without implementing the requested output.

### #3686 — publication evidence, not a compiler repro

The complete published-release census contains 26 releases and 73 assets:
zero macOS assets, with Linux assets on all 18 published releases from
v1.7.2212 onward. One unpublished draft had zero assets at capture time.
Querying its empty tag with `gh release view ""` silently returns the latest
published release and its three assets; this explained and corrected the
orchestrator's apparent 27-release / 76-asset / 19-Linux count.

### #3708 — tested ICE forms still reject component expressions

On `main` and all 20 measured releases, tested vector and matrix component
expressions are rejected in array bounds, case labels, enumerators, bitfield
widths, global initializers and template value arguments. FXC accepts the tested
forms; DXC's own `const-expr.hlsl` test records the divergence as desirable
future support. The tested scalar-alias workaround also fails. This is a
language-compatibility decision, not an isolated parser regression.

### #3726 — the issue is the missing Sema check

The front end is silent on all measured builds. The DXIL path later reports
`local resource not guaranteed to map to unique global resource`; the first
fallback line misleadingly mentions exported library functions in a pixel
shader with none. SPIR-V accepts the as-filed source and emits a module
referencing the assignment targets rather than sources. Because the issue asks
for this input to be rejected, that module records acceptance and lowering
shape, not a miscompile. Making the resources `static`, as suggested in the
thread, changes the DXIL result to success and can create a false
cannot-reproduce conclusion.

### #3811 — validator gap persists, literal silence does not

The exact shader now exits 0 with
`warning: parameter 'result' is uninitialized when used here`, added in
v1.7.2308. Its DXIL body remains line-for-line identical to the reporter's:
an `undef`-seeded PHI reaches arithmetic and the output, and validation accepts
it. The straight-line spelling is still rejected by
`InstrNoReadingUninitialized`. The validator explicitly exempts PHI nodes and
does not follow the propagated value. A local-variable restatement remains
fully silent, so the warning narrowed the spelling but did not close the hole.

## Duplicate determination for #3811

**Related, not a duplicate.** #3009 feeds literal `undef` directly into
arithmetic; #3706 uses an uninitialised structured-buffer index; #3693 is a
nested out-of-bounds subscript that becomes `undef`. #3811 uniquely exercises
the DXIL validator's explicit PHI exemption and transitive flow into arithmetic.
A 2024 maintainer reply on #3009 also says the posted `out`-parameter example
is not the same issue and asks for a new report.

## Step-10 independent draft review

All five drafts were reviewed together twice by `gpt-5.6-sol`, a different
model: once before editing and again after the material rewrites. Concision was
the primary criterion and exact replacements were required. Suggestions were
applied selectively: unsupported intent and universal claims were removed,
while literal diagnostics, measured version ranges, IR details and stale-text
findings were retained. Each verdict records the reviewer.

## What this batch taught about the method

1. An absence predicate must be anchored on output only successful codegen can
   emit; otherwise a failed compile can satisfy “no diagnostic” for free.
2. Search `tools/clang/test/` before bisecting. #3708's intended FXC divergence
   was already documented there.
3. A `file:line:col:` prefix does not identify Sema; #3726's source-located
   message is emitted from DXIL lowering.
4. Never invent an `@mention`; verify the login in `issue.json`.
5. Release drafts must be queried by ID. An empty tag can silently resolve the
   latest published release and corrupt a census.
6. A harness-as-compiler cannot be driven by ordinary `bisect`; #2604 is the
   fifth measured case where it would confidently invert history.

These lessons were promoted into `SKILL.md`. Tooling was also tightened:
GitHub/compiler subprocess text is decoded as UTF-8; Godbolt annotation strips
one leading `//`; custom Godbolt sources now require explicit arguments for
every pane; and the annotation behavior has a regression test. Harness-aware
`bisect` remains documented rather than automatically detected.

## Proposed labels

None applied.

| # | Current | Proposed additions |
| --- | --- | --- |
| 2604 | `enhancement` | `api`, `up-for-grabs` |
| 3686 | `build`, `macos` | `enhancement` |
| 3708 | `fxc-disagrees` | `hlsl-next`, `usability` |
| 3726 | `incorrect-code` | `diagnostic`, `check-in-clang` |
| 3811 | `validation` | `incorrect-code`, `diagnostic`, `check-in-clang` |

## Validation

- The mandatory opening `reindex` re-scored **50 issues / 852 runs**. It found
  no changed verdict, stale capture or evidence-completeness gap; the only
  collation gap was empty `reviewed_by` on these five verdicts. Final reindex
  again reported every probe re-scoring as captured, none stale and no missing
  evidence.
- `python scripts/triage.py audit`: `no missing evidence in 50 issue(s)`.
- `python scripts/test_predicates.py`: `all predicate tests passed`, including
  the new single-marker Godbolt annotation regression.
- `python scripts/render_comments.py 010` was run after every draft edit and
  spliced all five current comments. `python scripts/render_overview.py`
  regenerated the 50-issue overview.
- All three published CE shortlinks resolved with the expected pane IDs. All
  **11 live panes** were recompiled through the CE API and passed claim-specific
  checks for diagnostics, exit codes, bindings and PHI shapes.
- The superseded #3708 identifiers named in the orchestrator notes had a
  known-positive control (`51xjeKra5`, three current-artifact matches) and
  **zero** current-artifact matches. Public drafts/report had ten commit-pinned
  source links and zero branch-relative or orphan-SHA citations.
- Checkout-path scanning first matched raw, JSON-escaped and forward-slash
  known positives (3/3), then found **zero** `C:\prj` leaks in the five issue
  directories and this report.
- All five verdicts have `reviewed_by`. `git status` shows changes only under
  `.github/skills/dxc-issue-triage/`.

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


### Draft — [#2604](https://github.com/microsoft/DirectXShaderCompiler/issues/2604) Handle -Fc in Compile API

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2604](https://github.com/microsoft/DirectXShaderCompiler/issues/2604).

This remains unimplemented on upstream `main` (`1.9.0.5433`, `13730886e`) and
all 21 measured release DLLs from v1.4.1907 through v1.9.2607.

For `-T ps_6_0 -E main -Fc out.asm`, both API entry points return a result
whose status is `E_INVALIDARG`:

```
IDxcCompiler::Compile    call=S_OK  status=0x80070057  "Unknown argument: '-Fc'"
IDxcCompiler3::Compile   call=S_OK  status=0x80070057  "Unknown argument: '-Fc'"
```

With `-Qunused-arguments`, compilation succeeds but `-Fc` is ignored: no file
and no `DXC_OUT_DISASSEMBLY`. `IDxcCompiler::Disassemble` returns a 4104-byte
listing, and `dxc.exe` writes an assembly file.

`-Fc` is
[`DriverOption` only](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/include/dxc/Support/HLSLOptions.td#L505);
the library parses `CoreOption`, while the driver includes `DriverOption`.
Simply adding `CoreOption` would only silence the error: the API compile path
does not use `opts.AssemblyCode` to produce `DXC_OUT_DISASSEMBLY`. The
implementation needs to make `Compile` return the requested listing.

There is also a documentation mismatch:
[`docs/SPIR-V.rst`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/docs/SPIR-V.rst#L4197-L4211)
says `-Fc` is recognized by library API calls, but the measured SPIR-V API
behavior is the same rejection/ignore split above.

I would treat this as an API enhancement rather than a compiler bug. Suggested
labels: `api`, and `up-for-grabs` if the 2024 invitation for a PR still stands.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3686](https://github.com/microsoft/DirectXShaderCompiler/issues/3686) Binary release artifacts for macOS

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3686](https://github.com/microsoft/DirectXShaderCompiler/issues/3686).

This remains true for published releases. I enumerated all 73 assets on the 26
published releases from v1.2.0-alpha through v1.9.2607:

| | Count |
| --- | ---: |
| published releases with a macOS asset | **0** |
| published releases with a Linux asset | **18** |

Linux first appeared in v1.7.2212 and is present on every published release
since. One unpublished draft had zero assets at capture time and is excluded
from those counts.

The checked-in pipeline configures `MacOS_Clang_Release` and
`MacOS_Clang_Debug` to build and test on `macOS-latest`; that job publishes
test results, not a binary artifact. The older DXIL-signing blocker cited in
the thread appears resolved at source level (`lib/DxilHash` and `dxildll` are
in-tree and not `WIN32`-gated), although nothing was built on macOS in this
triage. The later Apple code-signing/distribution concern remains a project
decision.

Suggested action: keep this as an enhancement request, or close it as
`wont-fix` if the stated no-plans position is still current. Suggested label
addition: `enhancement`.

---
<sub>Triaged with AI assistance. The counts come from the GitHub release API
and the CI claims from the checked-in pipeline configuration; please flag
anything that looks wrong.</sub>
````

### Draft — [#3708](https://github.com/microsoft/DirectXShaderCompiler/issues/3708) Component swizzling / vector indexing not considered a constant expression

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3708](https://github.com/microsoft/DirectXShaderCompiler/issues/3708).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`) and all 20 measured
releases from v1.4.1907 through v1.9.2607:

```
repro.hlsl:6:14: error: variable length arrays are not supported in HLSL
    int array[(10).x];
             ^
```

Tested component expressions also fail as enumerators, case labels, non-type
template arguments, bitfield widths, global initializers and `[numthreads]`
arguments:

```
enum E { A = v2.x };
             ^~~~ error: expression is not an integral constant expression
case v2.x:
     ^ error: case value is not a constant expression
```

The tested scalar-alias workaround fails because its initializer is likewise
not a constant expression; `constexpr` is not a DXC keyword.

Compiler Explorer: **https://godbolt.org/z/51xjeKra5**. FXC accepts the tested
FXC-compatible forms. Clang accepts `(10).x`, the exact filed case; its rejections of
`static const uint2` forms use the ordinary C++ non-`constexpr` rule and become
accepted when spelled `constexpr uint2`.

DXC explicitly excludes `HLSLVectorElementExprClass` and
`ExtMatrixElementExprClass` in
[`CheckICE`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/tools/clang/lib/AST/ExprConstant.cpp#L9035-L9036).
The existing
[`const-expr.hlsl` test](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/tools/clang/test/SemaHLSL/const-expr.hlsl#L379-L382)
records the FXC divergence with “It would be desirable to have this supported,”
so a fix must update that test.

The remaining question is which constant-expression rule DXC should use.
Suggested labels: `hlsl-next` and `usability`; keep `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3726](https://github.com/microsoft/DirectXShaderCompiler/issues/3726) Sema should not allow assignment to resource

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3726](https://github.com/microsoft/DirectXShaderCompiler/issues/3726).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`) and all 20 measured
releases from v1.4.1907 through v1.9.2607.

Compiler Explorer: **https://godbolt.org/z/77EjzsnP9** (a compute restatement
verified against the as-filed pixel-shader repro).

The front end remains silent; DXIL lowering performs the rejection:

```console
$ dxc -T ps_6_0 -E main repro.hlsl
error: exported library functions cannot have resource parameters or return value. Value: ?x0@@3V?$Texture2D@V?$vector@M$03@@@@A
repro.hlsl:15:10: error: local resource not guaranteed to map to unique global resource.
    a0 = r0;
         ^

$ dxc -T ps_6_0 -E main -fcgl repro.hlsl
# exit 0, empty stderr
```

Both messages come from
[`DxilCondenseResources.cpp`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/lib/HLSL/DxilCondenseResources.cpp#L697-L702),
via `LegalizeResourceUseHelper` in `DxilLowerCreateHandleForLib`. The first is
a catch-all fallback; its source comment says “Most likely storing to output
parameter,” while the diagnostic mentions library functions.

`-spirv` exits 0 without a diagnostic on all 19 SPIR-V-capable measured
releases. Its module binds `x0`/`x1`/`x2`, the assignment targets, while
`r0`/`r1`/`r2` do not appear. Because this issue asks for the as-filed source
to be rejected, that is evidence of acceptance and lowering shape, not a
miscompile claim. Clang trunk also accepts the construct, but lowers through
`r0`.

There is a re-checking trap:

| `x0`/`x1`/`x2` form | DXIL | SPIR-V |
| --- | --- | --- |
| global, as filed | lowering error | exit 0; binds `x0`/`x1`/`x2` |
| `static`, per the 2024 comment | exit 0; binds `r0`/`r1`/`r2` | exit 0; resource operands become `OpUndef` |
| function-local | exit 0 | exit 0 |

Applying the standing “should be static” correction therefore makes the DXIL
half appear fixed, while the as-filed bound-global form still reproduces.
Scoping any Sema rule across these forms is a language-design decision.

Suggested labels: `diagnostic` and `check-in-clang`. I am not proposing
`correctness`, because the as-filed input is expected to be rejected, nor
re-adding `spirv`, which was deliberately removed during the 2024 reframing.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3811](https://github.com/microsoft/DirectXShaderCompiler/issues/3811) Reading uninitialized value in dynamic loop produces undef with no error/warning

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3811](https://github.com/microsoft/DirectXShaderCompiler/issues/3811).

The validator gap still reproduces on `main` (`1.9.0.5433`, `13730886e`), but
the title's “no error/warning” is now stale for the exact filed shader. Since
v1.7.2308, dxc emits:

```
repro.hlsl:7:3: warning: parameter 'result' is uninitialized when used here [-Wparameter-usage]
                result += values[i];  // <-- This will not
                ^~~~~~
repro.hlsl:3:28: note: variable 'result' is declared here
```

Compilation still exits 0 and validation passes. The emitted `main` is
line-for-line identical to the DXIL in the issue, including:

```
%7 = phi float [ %10, %5 ], [ undef, %4 ]
%10 = fadd fast float %9, %7
%15 = phi float [ undef, %0 ], [ %10, %13 ]
```

The straight-line control remains rejected:

```
variant-straightline.hlsl:5:9: error: Instructions should not read uninitialized value.
note: at '%4 = fadd fast float %3, undef' in block '#0' of function 'main'.
Validation failed.
```

Exit is `0x80004005`. The asymmetry exists on both v1.4.1907 and v1.9.2607.

The mechanism is the explicit PHI exemption in
`lib/DxilValidation/DxilValidation.cpp`:

```cpp
if (isa<UndefValue>(op)) {
  bool LegalUndef = isa<PHINode>(&I);
  if (!LegalUndef)
    ValCtx.EmitInstrError(&I, ValidationRule::InstrNoReadingUninitialized);
}
```

The rule catches literal `undef` operands. Through the loop, the `fadd`
operand is a PHI and the PHI is exempt. That exemption dates to the repository's
first commit (`6ee4074a4`).

The warning is parameter-specific: with an uninitialized local, the same loop
still exits 0 with no warning or error and emits the same `undef`-seeded PHI.
The hole reproduces on all 20 measured releases; only silence has a boundary
(8 releases silent, 12 warning from v1.7.2308).

Compiler Explorer: **https://godbolt.org/z/57zn3j6YK**. It shows dxc 1.6.2112
silent, dxc trunk warning, and Clang trunk emitting a similar PHI without an
uninitialized-value diagnostic. The Clang pane stops before DXIL validation.

Keep `validation`; suggested additions are `incorrect-code`, `diagnostic` and
`check-in-clang`. Whether to track `undef` through PHIs in validation or add a
front-end diagnostic covering locals is a maintainer design decision.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- **Sampling is strongly biased.** These five old open issues were deliberately
  selected for varied evidence shapes and a blind duplicate test, not sampled
  randomly. They over-represent long-lived defects and unimplemented requests
  and do not estimate backlog health.
- “All releases” in this report always means the explicitly measured set:
  usually the 20 bisectable tags from v1.4.1907 through v1.9.2607; #2604's API
  harness covered 21 cached release DLLs.
- #3686 measures published GitHub assets, not every private or CI-produced
  artifact. The unpublished draft had zero assets only at capture time.
- #3726's release Sema history starts at v1.5.2010 in the combined predicate;
  v1.4.1907 lacked SPIR-V codegen and was re-probed front-end-only.
- #3811's Clang Compiler Explorer pane reaches front-end LLVM IR, not DXIL
  validation; it supports only the front-end-silence comparison.
- Earlier batches 006–009 still contain citations to orphaned `ab5400907`.
  Their immutable binary-version captures should remain verbatim, but the
  orchestrator must decide whether to rewrite those report/verdict citations to
  live upstream provenance in a separate cleanup.
