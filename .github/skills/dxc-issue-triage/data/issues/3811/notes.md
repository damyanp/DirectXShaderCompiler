# Notes — #3811 "Reading uninitialized value in dynamic loop produces undef with no error/warning"

Filed 2021-06-02, label `validation`, **0 comments**. Ground truth: local **Debug** build,
`dxc --version` reports `1.9.0.5433 (triage, ab5400907)`; source-identical to upstream `main`
at **13730886e**. (`ab5400907` is a fork-local merge orphaned by a history rewrite and
resolves nowhere — cite `13730886e`.)

## Verdict in one line

The underlying validator gap still holds, and the mechanism is exactly what the reporter
guessed — but the issue's literal silence claim is now wrong: **dxc has warned on this exact
repro since v1.7.2308.** The DXIL validator still accepts the module, and the warning does not
cover the same defect written with a local variable.

## What was run

`cmd.txt` is `-T vs_6_0 repro.hlsl` — the reporter's command, unmodified. No entry point flag
(defaults to `main`), no `-Fo` (so dxc disassembles to stdout), default optimisation.
`repro.hlsl` is the issue body verbatim, tabs and comments included.

Two predicates, because the two halves of the report have diverged:

| file | asserts | main-debug |
| --- | --- | --- |
| `match.json` | an undef-seeded `phi float` reaches the DXIL **and** no `error:` — i.e. the module was accepted | **repro** |
| `match-silent.json` | the same, **and** no `warning:` either — the reported wording verbatim | **no-repro** |

## Claim (a): the loop version — `out-main-debug.txt`

Exit **0**. The `define void @main()` block is **line-for-line identical** to the DXIL the
reporter pasted in 2021 — 27 lines, no differences
(`manual-case-dxil-identity.txt`, re-derivable with `compare-dxil.py`):

```
  %7 = phi float [ %10, %5 ], [ undef, %4 ]
  %10 = fadd fast float %9, %7
  %15 = phi float [ undef, %0 ], [ %10, %13 ]
  call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 0, float %15)  ; StoreOutput(outputSigId,rowIndex,colIndex,value)
```

The uninitialised accumulator is seeded with `undef`, the `undef` reaches a floating-point add,
and on the `count <= 0` path an unconditional `undef` is written straight to the output. DXIL
validation passes.

What is new since 2021 is one line above it:

```
repro.hlsl:7:3: warning: parameter 'result' is uninitialized when used here [-Wparameter-usage]
                result += values[i];  // <-- This will not
                ^~~~~~
repro.hlsl:3:28: note: variable 'result' is declared here
```

(`repro.hlsl` is the issue body's shader byte-for-byte, no added header, so those line numbers
are the reporter's own.)

## Claim (b): the straight-line version — `variant-straightline-main-debug.txt`

The reporter's own commented-out line, uncommented, loop removed. It gets the same
`-Wparameter-usage` warning and then exits **0x80004005** (E_FAIL — an ordinary diagnosed error,
not an internal failure):

```
error: validation errors

variant-straightline.hlsl:5:9: error: Instructions should not read uninitialized value.
note: at '%4 = fadd fast float %3, undef' in block '#0' of function 'main'.
Validation failed.
```

Claim (b) confirmed, and it is the **DXIL validator** — not Sema — that rejects it. Also run on
both ends of the release range: `variant-straightline-v1.4.1907.txt` (2019) and
`variant-straightline-v1.9.2607.txt` both fail the same rule, so the asymmetry between the two
spellings is unchanged for as long as it is checkable. Only the wording differs — the 2019
validator prints `at 0x… inside block #0 of function main Instructions should not read
uninitialized value`, without source location.

## Why the loop escapes: the source says so, in one line

`lib/DxilValidation/DxilValidation.cpp`, the operand scan that emits
`ValidationRule::InstrNoReadingUninitialized`:

```cpp
for (Value *op : I.operands()) {
  if (isa<UndefValue>(op)) {
    bool LegalUndef = isa<PHINode>(&I);
    ...
    if (!LegalUndef)
      ValCtx.EmitInstrError(&I, ValidationRule::InstrNoReadingUninitialized);
```

The rule is purely local and syntactic: it fires only where an operand is *literally*
`UndefValue`, and PHI nodes are explicitly exempt.

- straight-line: `fadd`'s operand **is** `undef` → rejected.
- loop: `fadd`'s operand is `%7`, a *PHINode*, so the rule does not fire on the `fadd`; and the
  PHI that carries the `undef` is exempt by name. Nothing else looks.

The reporter wrote "because undef is permitted in phi nodes, it seems" — that is the code, not
an approximation of it.

The exemption is as old as the repository. `git log --follow -S "isa<PHINode>(&I)"` on that file
returns exactly one commit, `6ee4074a4` (2016-12-28, "first commit"), where it is spelled
`if (!isa<PHINode>(&I)) { for (Value *op : I.operands()) { if (isa<UndefValue>(op)) ... }`.
Same exemption, restructured since. It predates every probeable release and the report by five
years, which is consistent with the measured history below.

## History

**`match.json` — the defect: `always-repro'd` across v1.4.1907..v1.9.2607.** All 20 bisectable
releases probed linearly, **0 invalid probes**. v1.4.1907 (2019-07) is the bisection floor, so
this means "for as long as it is possible to check". The 2021-06-02 report is nevertheless
covered: v1.6.2104 (2021-04-20) predates it and reproduces. The catalog's v1.5.2003 hole is
irrelevant here for the same reason, so it was not run by hand.

**`match-silent.json` — the reported wording: repro on 8 releases, then a single clean
transition at v1.7.2308.**

```
v1.4.1907 v1.5.2010 v1.6.2104 v1.6.2106 v1.6.2112 v1.7.2207 v1.7.2212 v1.7.2212.1   repro
v1.7.2308 ... v1.9.2607 (12 releases)                                               no-repro
```

Attribution: `1380cf88e` — "Add diagnostics for uninitialized `out` parameters (#5047)",
2023-03-01, which adds `warn_hlsl_uninit_out_param` in `InGroup<HLSLParameterUsage>`
(`tools/clang/include/clang/Basic/DiagnosticSemaKinds.td`). `git merge-base --is-ancestor` puts
it inside v1.7.2308 and outside v1.7.2212.1. The window holds 257 commits, 5 of which touch that
file, and `git log -S warn_hlsl_uninit_out_param v1.7.2212.1..v1.7.2308` returns that one commit
— so the attribution is strong, though the fix was not built and tested at the commit.

## The warning does not cover the defect — `variant-local-uninit-main-debug.txt`

`-Wparameter-usage` is, as its name says, about parameters. Write the identical uninitialised
loop accumulation over a **local variable** and today's `main` is completely silent:

```hlsl
float main (int count : IN) : OUT
{
	float result;
	for (int i = 0; i < count; i++)
		result += values[i];
	return result;
}
```

Exit 0, no error, **no warning**, and the same IR:

```
  %6 = phi float [ %10, %5 ], [ undef, %4 ]
  %10 = fadd fast float %9, %6
  %15 = phi float [ undef, %0 ], [ %10, %13 ]
```

It matches **both** predicates on main-debug, including `match-silent.json`
(`variant-local-uninit-main-debug--match-silent.txt`). So the issue's literal claim — undef in
the DXIL with no error *and* no warning — still reproduces on today's `main`; it just needs the
`out` parameter replaced by a local. The 2023 diagnostic narrowed the spelling that is caught,
not the hole.

## Not optimisation-dependent — `variant-od-main-debug.txt`

`-T vs_6_0 -Od repro.hlsl`: exit 0, same warning, same shape
(`%10 = phi float [ undef, %7 ], [ %13, %8 ]`, `%13 = fadd fast float %10, %12`), scored `repro`.
The undef is not an artefact of one optimisation level.

## Controls

| capture | shader | declared | result |
| --- | --- | --- | --- |
| `variant-control-initialized-main-debug.txt` | one line added: `result = 0.0;` | `no-match` | ✔ emits `phi float [ %10, %5 ], [ 0.000000e+00, %4 ]` — same phi, constant instead of undef |
| `variant-control-initialized-main-debug--match-silent.txt` | as above, second predicate | `no-match` | ✔ |
| `variant-straightline-main-debug.txt` | the diagnosed spelling | `no-match` | ✔ (it errors) |
| `variant-local-uninit-main-debug.txt` | local instead of `out` param | `match` | ✔ |
| `variant-od-main-debug.txt` | `-Od` | `match` | ✔ |
| `variant-compute-main-debug.txt` | compute restating (for the CE link) | `match` | ✔ |

This is the standard missing-diagnostic control pair and it needs both arms: `straightline`
proves the check exists and the pipeline reaches it, `control-initialized` proves the predicate
is not firing on everything.

Predicate narrowness was deliberate and is recorded in `match.json`'s `note`. Matching `undef`
anywhere would fire on correct shaders — `loadInput`'s trailing `gsVertexAxis` operand is `undef`
in every non-GS shader and is in the reporter's own paste, and the compute variant's
`bufferStore` carries three more `float undef` operands for unused components. Matching `undef`
reaching an arithmetic *dx.op* would not work either: the arithmetic here is a plain LLVM `fadd`.

## Compiler Explorer

https://godbolt.org/z/57zn3j6YK — read back via `/api/shortlinkinfo/57zn3j6YK`: three panes,
`dxc_1_6_2112`, `dxc_trunk`, `hlsl_clang_trunk`, all `-T cs_6_0`. Full pane text in
`manual-case-godbolt-verify.txt`.

It publishes `variant-compute.hlsl`, a compute restating, because Clang's DXIL backend cannot
lower vertex signature I/O and a `vs_6_0` pane would be noise about the stage. The restating was
verified to still reproduce locally before it was adopted; the stage-accurate `vs_6_0` original
is the local evidence.

- `dxc_1_6_2112`: exit 0, **no warning at all**, `%.0 = phi float [ %5, %.lr.ph ], [ undef, %.lr.ph.preheader ]`.
- `dxc_trunk`: exit 0, the `-Wparameter-usage` warning, **identical** DXIL. The link therefore
  shows the transition itself, side by side.
- `hlsl_clang_trunk`: exit 0, `%5 = phi nsz float [ undef, %0 ], [ %11, %8 ]` feeding
  `fadd`, and **no uninitialised-value diagnostic** — only an unrelated `-Wsign-conversion`.

### Clang controls — `manual-case-clang-control.txt`

A cross-compiler silence needs a control as much as a cross-compiler error does. Three cases
through `hlsl_clang_trunk`, generated by the committed `ce-clang-control.py`:

| case | exit | uninit diagnostics | undef-seeded float phis |
| --- | --- | --- | --- |
| loop repro | 0 | 0 | 1 |
| straight-line | 0 | **0** | 0 (`main()` folds to `ret void`) |
| initialized | 0 | 0 | 0 |

Clang emits no uninitialised-value diagnostic for **either** spelling — including the one DXC
rejects — so the honest finding is that clang-dxc has no equivalent of `-Wparameter-usage` at
all, not that it merely misses the loop case. The `initialized` row is the reader's control: it
shows the phi count really does go to 0 on correct code, so the 0s above are measurements rather
than a broken parse.

**Limit:** CE's Clang pane emits pre-DXIL LLVM IR and does not run the DXIL validator, so it
cannot say anything about whether Clang's eventual validation would reject either spelling. Only
the front-end silence is evidence here.

## Labels

`validation` is **correctly** applied and should stay. The label means DXIL validation
specifically, and that is exactly what this is: the rule is `InstrNoReadingUninitialized` in
`lib/DxilValidation/DxilValidation.cpp`, the reporter's contrast is with what that rule catches,
and the exemption that lets the loop through is one line of that rule.

Proposed additions:

- **`incorrect-code`** ("Issues relating to handling of incorrect code") — the shader is invalid
  and the whole issue is how DXC handles it.
- **`diagnostic`** ("Issues for diagnostics") — the ask is a diagnostic that is not emitted, and
  the one that was added in 2023 does not cover the general case.
- **`check-in-clang`** — measured, and the answer is yes: clang-dxc shares the gap and does not
  even have the `out`-parameter warning. Recording the finding makes it findable during the
  Clang rebuild.

No removals. There are no comments on the issue, so there is no maintainer position that these
proposals might contradict — but equally, no history to draw on.

## Duplicate check against earlier undef issues

**Related, not a duplicate.** The closest prior issues exercise different checks:

- **#3009** passes a literal `undef` directly into arithmetic. Its 2024 maintainer reply also
  says an `out`-parameter example posted there is "not ... the same issue" and asks for a new
  report (`data/issues/3009/issue.json`). #3811 instead demonstrates the validator's explicit
  PHI exemption and transitive flow from that PHI into arithmetic.
- **#3706** passes an uninitialised value as a structured-buffer index; its decision point is
  whether the available uninitialised-use warning is enabled or complete, not whether
  `InstrNoReadingUninitialized` follows values through a PHI.
- **#3693** is an out-of-bounds vector/array subscript that becomes `undef` when nested inside
  another subscript. That is a Sema reachability hole, not uninitialised-value propagation.

The shared word `undef` describes the resulting IR, not one common defect. No duplicate action
is supported by the measured components and mechanisms.

## Assessment

`changed-behavior`, `still-valid-keep-open`, confidence **high**.

Still live: an uninitialised read reaches the emitted DXIL as `undef`, flows into
arithmetic and into the shader's output, and DXIL validation accepts it — unchanged on every one
of the 20 probeable releases and on `main`, with the same read written straight-line rejected
throughout. Differently than reported: the exact repro is no longer silent.

The reason to record it as `text_stale` rather than a footnote is that the title's "no
error/warning" is the first thing a maintainer spot-checking this issue will test, and it now
fails — which reads as "cannot reproduce" for a defect that is completely untouched.
