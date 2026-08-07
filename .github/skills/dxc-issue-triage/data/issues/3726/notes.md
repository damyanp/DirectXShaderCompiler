# #3726 — "Sema should not allow assignment to resource"

<https://github.com/microsoft/DirectXShaderCompiler/issues/3726> · open since 2021-04-29 ·
filed by jaebaek · label `incorrect-code` · 2 comments.

Ground truth: `main-debug`, a Debug build of **upstream `main` at
`13730886e6a9019e4e0823746470f3ab75341d6b`**. (The binary self-reports
`1.9.0.5433 (triage, ab5400907)`; `ab5400907` is a fork-local merge orphaned by a history
rewrite and resolves nowhere, so it is not cited. `git diff --name-only 13730886e HEAD`
excluding this skill's own directory is empty, so the compiler source is that commit.)

Prediction was written first, in `expected.md`, before any compiler ran.

---

## Verdict

**Reproduces, exactly as filed, on all 21 measured DXC builds.** All three of the issue's
assertions hold on `main`. The SPIR-V path also records a useful lowering detail: the
emitted module references the assignment targets rather than the sources.

| | as filed | on `main` (13730886e) |
|---|---|---|
| front end (Sema) diagnoses it | should, doesn't | **doesn't** — `-fcgl` exits 0, empty stderr, on all 21 builds |
| DXIL back end diagnoses it | yes | **yes** — and the first line of the message is misleading |
| SPIR-V back end diagnoses it | no | **no** — exit 0, and it binds the assignment targets |

New relative to the issue text: the **successor front end accepts it too**.
`hlsl_clang_trunk` compiles the same construct at exit 0 with no diagnostic.

---

## What was tested

`repro.hlsl` is the issue body verbatim, unreformatted — the diagnostics quote line numbers
(`15`, `16`, `17`), so reflowing it would silently invalidate every quoted line.

`cmd.txt` runs three invocations per capture, which is what makes the *layer* question
measurable rather than inferred:

```
-T ps_6_0 -E main repro.hlsl              # DXIL
-T ps_6_0 -E main -spirv repro.hlsl       # SPIR-V
-T ps_6_0 -E main -fcgl repro.hlsl        # front end only: stop after high-level IR
```

`-fcgl` is the instrument for the whole issue. It emits the front end's IR and never runs
DXIL lowering, so a clean `-fcgl` *is* "Sema had nothing to say". `cmd-as-filed.txt` records
that the report itself implies only line 1.

> A `-Zs` probe was tried first and discarded: in DXC `-Zs` means "generate small PDB",
> **not** syntax-only. It runs a full compile and answers a different question.

### Ground truth output (`out-main-debug.txt`)

```
$ dxc -T ps_6_0 -E main repro.hlsl                    [exit] 0x80004005
error: exported library functions cannot have resource parameters or return value. Value: ?x0@@3V?$Texture2D@V?$vector@M$03@@@@A
repro.hlsl:15:10: error: local resource not guaranteed to map to unique global resource.
    a0 = r0;
         ^
                              ... and the same pair again for x1/r1 and x2/r2.

$ dxc -T ps_6_0 -E main -spirv repro.hlsl             [exit] 0        (no diagnostics)
$ dxc -T ps_6_0 -E main -fcgl repro.hlsl              [exit] 0        (no diagnostics)
```

`0x80004005` is `E_FAIL`, which is what dxc returns on Windows for an ordinary diagnosed
error — not an internal failure.

---

## Which layer emits the diagnostic

This is the substance of the issue, so it is corroborated from the tree, not from output.
`manual-case-sema-absence.txt` (regenerate with `make-sema-absence.py`) records every search
with its command line; each absence check is paired with a known-positive over the same
paths with the same tool.

* **The message is the DXIL back end's.**
  `lib/HLSL/DxilCondenseResources.cpp:699` holds `"local resource not guaranteed to map to
  unique global resource."` in `ResourceUseErrors::ErrorText`, and `:701` holds
  `"exported library functions cannot have resource parameters or return value."`. Nothing
  under `tools/clang/lib/` or `tools/clang/include/` contains either string. (Searching all
  of `tools/clang/` matches ~30 files — every one a FileCheck test asserting the back end's
  output, which is why the search is scoped to sources.)
* **It is reported from a lowering pass, not from code generation.**
  `LegalizeResourceUseHelper` (`DxilCondenseResources.cpp:807`) is driven by
  `DxilLowerCreateHandleForLib`, pass `-hlsl-dxil-lower-handle-for-lib`. `dxc -Odump` for
  `ps_6_0` shows it running roughly 150 passes after `-dxilgen`.
* **Sema has no rule of this kind.** `DiagnosticSemaKinds.td` contains 191 `err_hlsl`
  diagnostics; exactly one is named for a resource
  (`err_hlsl_invalid_resource_type_on_intrinsic`, "cannot %0 from resource containing %1"),
  and it is about intrinsic arguments.
* **The front end is not simply absent from this code path.** `control-sema-mismatch.hlsl`
  makes the *same* assignment ill-typed and Sema rejects it at once:
  `error: cannot convert from 'Texture2D<float4>' to '__restrict SamplerState'`, with
  `-fcgl` failing. So the front end type-checks the very expression #3726 is about. It just
  has no rule that says assigning a resource is itself illegal.

### The first error line is misleading

`ResourceUseErrors::UserCallsWithResources` is a **catch-all fallback**
(`DxilCondenseResources.cpp:1016-1017`), whose own comment reads `// Most likely storing to
output parameter`. That is why a **pixel shader containing no library functions** is told
that "exported library functions cannot have resource parameters or return value", against
a mangled global name and with no source location. The accurate, source-located message is
the second line. Worth noting even if the issue is otherwise resolved by design.

---

## SPIR-V: undiagnosed, with a measurable lowering shape

`-spirv` exits 0 on every release that has SPIR-V codegen, and the module it emits binds
`x0`/`x1`/`x2` (the assignment's **targets**) at bindings 3/4/5. `r0`/`r1`/`r2`, the
resources actually assigned *from*, do not appear anywhere in the module.

The DXIL path rejects the source, the SPIR-V path accepts it, and neither is checked by the
front end. The issue body anticipated the difficulty exactly ("the assignment is not locally
detectable at `a0 = r0`" — an analysis is needed to find `OpStore` to a resource). Because
the issue asks for this source to be rejected, the emitted module is evidence of acceptance
and lowering shape, not evidence of a miscompile.

---

## The three declaration forms disagree — and this is the design question

Same `a0 = r0;` assignment in all three; only where `x0`/`x1`/`x2` are declared changes.
The front end is silent in all three.

| form of `x0`/`x1`/`x2` | file | DXIL | SPIR-V |
|---|---|---|---|
| **global** (as filed) | `repro.hlsl` | error from the lowering pass | exit 0, **binds `x0`/`x1`/`x2`, never `r0`/`r1`/`r2`** |
| **`static`** (damyanp's comment) | `case-static.hlsl` | **exit 0** — binds `r0`/`r1`/`r2` | exit 0, **no resource variables at all**: `OpUndef %type_2d_image`, `OpUndef %type_sampler`, `OpUndef %_ptr_Uniform_type_RWByteAddressBuffer`, then `OpAccessChain`/`OpLoad`/`OpSampledImage` off those undefs |
| **function-local** (PR #3721's shape) | `case-local.hlsl` | exit 0 | exit 0 |

So a blanket Sema rule "assignment to a resource is illegal" would reject two forms that
DXC accepts today. The as-filed **bound global resource** form is the one the issue asks
Sema to reject. **Scoping that rule is a language-design decision** and is deliberately
not made here.

### A trap for anyone re-checking this issue

damyanp's standing comment says "(For reference, x0, x1 and x2 in the repro should be
static)". With `static`, DXC's **DXIL path compiles cleanly**. A reader who applies that
correction and re-runs will conclude "cannot reproduce" — while the as-filed repro still
fails, and the `static` form has its own (different, SPIR-V-only) defect.

**`text_stale` was considered and declined.** SKILL.md holds it to a high bar because it is
a claim about someone's writing. The title and body are accurate descriptions of what the
compiler does today — and the title was in fact *updated* on 2024-07-16, from "[SPIR-V] do
not allow assignment to resource" to "Sema should not allow assignment to resource", which
is exactly where the defect is. The comment is a clarification of intent, not a claim about
behaviour, and it is not wrong so much as it changes the subject. Recorded here so collation
can revisit the call rather than have to rediscover the question.

---

## History

Two predicates, bisected separately, so that "Sema learned to reject this" and "the DXIL
error changed shape" cannot collapse into one verdict.

* **`match.json`** — positive-only regex on `local resource not guaranteed to map to unique
  global resource`. `--linear`: **`always-repro'd across v1.4.1907..v1.9.2607`**. All 20
  releases plus `main` score `repro`; no invalid probes. The bisection floor predates the
  2021-04 report by 21 months, so there is no unexamined window.
* **`match-sema.json`** — **inverted polarity: a match would mean the issue is FIXED.** It
  looks for a diagnostic under the `-fcgl` invocation that is not the back-end message.
  `--linear`: **`never-repro'd across v1.5.2010..v1.9.2607`, 1 release skipped as
  unprobeable.** The front end has never diagnosed this.

The `invalid-probe` on v1.4.1907 is an artefact and was predicted in the predicate's own
note: that release has no SPIR-V codegen, and `cmd.txt` line 2 therefore prints a
feature-absence marker that demotes the whole capture — even though line 3, the `-fcgl`
line, ran fine. `variant-fcgl-only-v1.4.1907--match-sema.txt` re-runs just the `-fcgl`
invocation on v1.4.1907 and preserves that datapoint: **no-repro**, i.e. silent there too.

`manual-case-layer-history.txt` (from `make-layer-history.py`, which runs no compiler and
reads only the committed captures) tabulates all 21 builds × 3 layers. Its shape is flat:
`0x80004005`/`yes` for DXIL, `x0+x1+x2` for SPIR-V, `0x00000000`/`none` for `-fcgl`, on
every row from v1.5.2010 onward.

### Controls

| capture | predicate | expected | got |
|---|---|---|---|
| `variant-sema-mismatch-main-debug--match-sema.txt` | `match-sema` | match | ✔ repro |
| `variant-sema-mismatch-main-debug.txt` | `match` | no-match | ✔ no-repro |
| `variant-correct-main-debug*.txt` | both | no-match | ✔ no-repro |
| `variant-static-main-debug*.txt` | both | no-match | ✔ no-repro, exit 0 |
| `variant-local-main-debug.txt` | `match` | no-match | ✔ no-repro, exit 0 |
| `variant-cs-dxil-main-debug.txt` | `match` | match | ✔ repro |
| `variant-cs-fcgl-main-debug.txt` | `match` | no-match | ✔ no-repro |
| `variant-cs-spirv-main-debug.txt` | `match` | no-match | ✔ no-repro, exit 0 |
| `variant-cs-trivial-main-debug.txt` | `match` | no-match | ✔ no-repro, exit 0 |

Both predicates are shown to discriminate: each has an input it fires on and inputs it does
not.

---

## Compiler Explorer

**<https://godbolt.org/z/77EjzsnP9>** — four panes, link read back and verified
(compiler ids and source round-trip intact); full pane output in
`manual-case-godbolt-verify.txt`.

The published source is `repro-cs.hlsl`, a **compute restating** of the repro, because
Clang's DXIL back end cannot lower a pixel shader writing `SV_Target` and the issue's repro
is exactly that. It was verified to reproduce the same behaviour before adoption
(`variant-cs-dxil-*`, `variant-cs-fcgl-*`, `variant-cs-spirv-*`); `repro.hlsl` remains the
stage-accurate local evidence, and `godbolt-note.txt` is the banner naming what to look at.

| pane | result |
|---|---|
| `dxc_1_6_2112` | same two errors, `<source>:50:10` (line 50 because of the banner) |
| `dxc_trunk` | identical |
| `dxc_trunk -spirv` | exit 0; `OpName %x0`, `OpDecorate %x0 Binding 1`; no `r0` |
| `hlsl_clang_trunk` | **exit 0, no diagnostic**, binding table names **`r0`**, and `@r0 = external constant %"RWBuffer<float4>"` — it lowers the store through `r0` |

### The Clang result, with its control

`hlsl_clang_trunk` accepting `repro-cs.hlsl` is only evidence because the control says so.
`control-cs-trivial.hlsl` — the same shader with the assignment removed — compiles at exit 0
on **both** `dxc_trunk` and `hlsl_clang_trunk` with identical flags, so Clang's back end can
lower this stage and this resource type. `manual-case-clang-control.txt` is the 2×2 matrix
(two sources × two compilers, identical arguments), generated by `make-clang-control.py`,
which prints every request it makes.

```
source                     compiler              exit  diags
control-cs-trivial.hlsl    dxc_trunk                0      0
control-cs-trivial.hlsl    hlsl_clang_trunk         0      0
repro-cs.hlsl              dxc_trunk                5      2
repro-cs.hlsl              hlsl_clang_trunk         0      0
```

So the successor front end does not diagnose this either — and, unlike either DXC back end,
it gives the assignment the copy semantics that make `x0[...]` write **`r0`**. Whether that
is the intended answer or a diagnostic Clang has not implemented yet is a question for the
people rebuilding HLSL in Clang; it is not answered here. `-fsyntax-only` was not needed:
Clang's back end was never the obstacle.

---

## Labels

Current: `incorrect-code`. Proposed additions, no removals:

* **`diagnostic`** — the whole issue is about a diagnostic being in the wrong layer, and the
  message that does appear names library functions in a shader that has none.
* **`check-in-clang`** — the Clang answer is now measured and it differs from both DXC back
  ends; the label routes it to the people who have to decide whether Clang should diagnose.

### `spirv` was deliberately removed — deferred to a maintainer, not proposed

The timeline (`gh api .../issues/3726/timeline`) shows this was not an oversight:

```
2021-04-29  jaebaek  +spirv,  titled "[SPIRV] do not allow assignment to resource"
                              renamed to "[SPIR-V] do not allow assignment to resource"
2024-07-16  damyanp  +incorrect-code
2024-07-16  damyanp  -spirv
2024-07-16  damyanp  milestone: Backlog
2024-07-16  damyanp  renamed to "Sema should not allow assignment to resource"
```

`spirv` was dropped in the same minute as the retitle, as part of reframing this from a
SPIR-V bug into a front-end one. Re-adding it would reverse an explicit maintainer decision,
so it is **not** proposed. But the reframing predates the measurement in this file: SPIR-V accepts the as-filed source
and emits a module referencing the assignment targets at exit 0. Whether that reinstates
`spirv` here is a maintainer's call, and is raised in the draft comment rather than decided.

`hlsl-next` was also considered (the scoping question is arguably a language-version
question) and left off: it is a maintainer's call whether this needs a language change or
just a Sema rule, and the label would pre-empt it.

---

## Assessment

* **Status:** `repros` — all three assertions, unchanged since the report.
* **Repro quality:** `complete`.
* **Confidence:** `high`. Three independent lines of evidence agree: output on 21 builds,
  the emitting source in the tree, and Compiler Explorer.
* **Suggested action:** `still-valid-keep-open`.

Actionable without any design decision:

1. The `UserCallsWithResources` fallback text is wrong for this input and could say what is
   actually happening (a resource was stored into an `out` parameter).
2. The SPIR-V path binds the assignment's target instead of its source; that lowering shape
   is independent of where the missing diagnostic eventually lands.

Needing a decision (deliberately not made here): whether Sema should reject assignment to a
resource, and how narrowly — `case-static.hlsl` and `case-local.hlsl` show a blanket rule
would reject code DXC accepts today, and `hlsl_clang_trunk` shows the successor
front end currently accepts all three.
