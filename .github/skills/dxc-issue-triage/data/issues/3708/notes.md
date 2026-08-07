# Issue 3708 — Component swizzling / vector indexing not considered a constant expression

Ground truth: `main-debug`, a clean Debug build of upstream `main`
`13730886e6a9019e4e0823746470f3ab75341d6b`. Its `dxc --version` self-reports
`1.9.0.5433 (triage, ab5400907)`; that hash is a fork-local merge orphaned by a history
rewrite and resolves nowhere, so cite `13730886e`.

**Verdict: still reproduces, on every one of the 20 probeable releases and on `main`. The
title is right and the body is narrower than the defect. It is a known, deliberate-looking
gap: DXC's own test suite pins the behaviour and annotates the FXC disagreement.**

## Verdict summary

| | |
| --- | --- |
| status | `repros` |
| repro quality | `complete` — the body gives a one-line minimal case, comment 1 a six-case matrix |
| history | `always-repro'd` across v1.4.1907..v1.9.2607, 20 of 20, no invalid probes |
| text stale | **no** — see below; the body is narrower than the defect but nothing in it is false |
| confidence | high |
| suggested action | `still-valid-keep-open` |

## What the issue says, and what is actually true

The body: `int array[10]` works, `int array[(10).x]` fails with
`variable length arrays are not supported in HLSL`, and *"This makes it impossible to use
components of constant vectors as array lengths."*

The array bound is not the rule. `variant-nonarray-ice-main-debug.txt` shows the same
operand refused in **three constant-expression contexts that have no array in them**, each
with its own diagnostic:

```
case-nonarray-ice-contexts.hlsl:9:14:  error: expression is not an integral constant expression
                                       enum E { A = v2.x };
case-nonarray-ice-contexts.hlsl:15:14: error: case value is not a constant expression
                                       case v2.x: r = 1; break;
case-nonarray-ice-contexts.hlsl:18:19: error: non-type template argument of type
                                       'unsigned int' is not an integral constant expression
                                       vector<float, v2.y> vv = 0;
```

So the **title** is the accurate description and the **body** is not: the component is not an
integral constant expression anywhere, and the array bound is simply where the reporter met
it. That matters for anyone spot-checking the issue, and it matters for scoping a fix — a
change confined to `BuildArrayType` would leave `case`, `enum` and `vector<T,N>` broken.

This is deliberately **not** recorded as `text_stale`. Nothing in the issue is false: the
body says the problem *"manifests when trying to define arrays"* and that it is *"impossible
to use components of constant vectors as array lengths"*, both of which are still exactly
true. It is narrower than the defect, not wrong about it, and the title covers the general
case. `text_stale` is for text a reader would believe *over* the compiler; a reader who
believes this body is not misled, only under-informed.

`variant-array-contexts-main-debug.txt` adds the rest of the array contexts — file-scope
`static`, `groupshared`, a struct member and a `cbuffer` member all give the VLA error, and
`[numthreads(v2.y,1,1)]` gives `'numthreads' attribute requires an integer constant`.

## Boundary of the behaviour

`variant-operand-shapes-main-debug.txt` and `variant-matrix-main-debug.txt`, measured. All
of these are refused as an array bound on `main`:

| bound | accepted? |
| --- | --- |
| `[10]` | **yes** |
| `[scalarLength]`, `static const uint scalarLength = 10` | **yes** |
| `[(10).x]` — swizzle of a literal | no |
| `[scalarLength.x]` — swizzle of a *scalar* | no |
| `[vectorLengths.x]`, `[vectorLengths[1]]` | no |
| `[uint2(20,30).x]`, `[uint2(20,30)[0]]` — rvalue vector | no |
| `[v2.r]` — colour-channel spelling | no |
| `[m22._11]`, `[m22._m00]`, `[m22[0][0]]` — matrix | no |
| `[(10).xx[0]]`, `[v2.x + v2.y]` | no |
| `[via]`, where `static const uint via = v2.x;` | no |

Two things worth pulling out.

**A `.x` on a plain `static const` scalar fails.** `scalarLength` alone is accepted;
`scalarLength.x` is not. Nothing about that involves a vector or an index, so "component
swizzling / vector indexing" is itself slightly narrow: it is the *node kind* that is
refused, not the presence of more than one component.

**The tested scalar-alias workaround does not work in DXC.** Folding the component into a
`static const` scalar does not work, because that scalar's initialiser is
itself not a constant expression, so the scalar is not usable as one either. `constexpr` is
not a DXC keyword (`error: unknown type name 'constexpr'`,
`manual-case-clang-control.txt` section B). Every spelling tried failed.

**HLSL language version makes no difference.** `variant-hv2018-` and `variant-hv2021-` both
reproduce, as do `-HV 2016` and `-HV 2017`. This is worth stating because
`Expr::isIntegerConstantExpr` takes two different code paths depending on it
(`ExprConstant.cpp:9427`), so "it fails at both defaults" is a measurement rather than an
assumption.

## Where the compiler rejects it

`err_hlsl_vla` is raised in `tools/clang/lib/Sema/SemaType.cpp:2142–2146` — an HLSL change
that turns any array type that came out as variable-length into an error. The bound became
variable because the constant evaluator would not fold it, and there are two HLSL-specific
reasons for that in `tools/clang/lib/AST/ExprConstant.cpp`:

- `CheckICE` lists `ExtMatrixElementExprClass` and `HLSLVectorElementExprClass` among the
  node kinds that are *"not an ICE, and not a legal subexpression for one"*
  (lines 9035–9036, both marked `// HLSL Change`);
- `IntExprEvaluator::VisitCastExpr` answers `Error(E)` for `CK_HLSLVectorToScalarCast` and
  `CK_HLSLMatrixToScalarCast` (lines 7749–7750, likewise `// HLSL Change`).

Which of the two is consulted depends on the language version:
`Expr::isIntegerConstantExpr` diverts to `EvaluateCPlusPlus11IntegralConstantExpr` — which
evaluates rather than consulting `CheckICE`'s node-class list — for `HLSLVersion >= 2021`
(lines 9427–9429). Since the repro fails identically at `-HV` 2016, 2017, 2018 and 2021,
both paths refuse it; this write-up does not claim which one fires for a given input, only
that neither folds it.

And the folding that does exist is the wrong shape. `VisitHLSLVectorElementExpr` occurs
exactly twice in the file — a declaration at 5693 and its definition at 5706 — both inside
`VectorExprEvaluator`, i.e. it can only fold a swizzle whose *result is a vector*
(its own comment gives `float4 a = (0.0).xxxx;`). An array bound, a `case` label and a
template argument all need a scalar, and no scalar evaluator has a visitor for the node.
`VisitExtMatrixElementExpr` occurs **zero** times, which is why every matrix spelling fails
too. (Counted with `Select-String`, not the agent `grep` tool, and with a known-positive
control in the same file: `VisitCastExpr` returns 34.)

Both rejection sites date to `6ee4074a4` (2016-12-28), DXC's initial open-source commit —
consistent with, and an explanation for, the 20-of-20 release history below.

`v2[1]` is a different AST shape from `v2.x` and so is refused by different code: it is a
`CXXOperatorCallExpr` calling the vector's `operator[]`, which no evaluator here folds and
which `CheckICE` refuses as a call (line 9133) — that clause is stock clang, not an HLSL
change. It is the same user-visible defect, but a fix that only taught the evaluator about
swizzles would not cover it.

## This is pinned by DXC's own test suite

`tools/clang/test/SemaHLSL/const-expr.hlsl:379–382`:

```hlsl
  // Note: here dxc is different from fxc, where a const integral vector can be used in ICE.
  // It would be desirable to have this supported.
  float arr_vc_One[vc_One.x];  /* expected-error {{variable length arrays are not supported in HLSL}} fxc-pass {{}} */
  float arr_vc_Two[vc_Two.x];  /* expected-error {{variable length arrays are not supported in HLSL}} fxc-pass {{}} */
```

Those lines were added by `6322c8ca3` on **2017-08-29** (PR #605), three and a half years
before this issue was filed. `fxc-pass {{}}` is the test suite's own record that FXC accepts
what DXC rejects, and the comment above it says the gap is known and undesired. So the
behaviour is not an oversight anyone has to be convinced of — but it *is* asserted by a
`-verify` test, which any fix has to update.

## FXC and clang, measured rather than asserted

`manual-case-fxc.txt`, generated by the committed `run-fxc-3708.py` (FXC 10.1 from the
Windows 10 SDK, `10.0.26100.0`):

| source | FXC `/T ps_5_0` | DXC `-T ps_6_0` |
| --- | --- | --- |
| `repro.hlsl` (`int array[(10).x]`) | exit 0 | 1 error |
| `control-literal.hlsl` (`int array[10]`) | exit 0 | exit 0 |
| `case-array-bound-matrix.hlsl` (comment 1's six) | exit 0 | 4 errors |
| `case-nonarray-ice-contexts.hlsl` | exit 1 — **invalid probe**, FXC has no `enum` | 3 errors |
| `case-ice-fxc-portable.hlsl` (`case` + `vector<T,N>` + file-scope array) | exit 0 | 3 errors |

The fourth row is why the fifth exists. FXC answers
`X3000: syntax error: unexpected token 'enum'` — it cannot parse the file at all, so its
non-zero exit says nothing about constant expressions. Rewritten without the enumerator,
the last row is the strongest evidence here: FXC compiles a source containing `case v2.x:`
and `vector<float, v2.y>` cleanly, so its acceptance is not special-casing array bounds
either.

Clang (`hlsl_clang_trunk` on Compiler Explorer) needed a control before it could be read at
all, and the control changed the answer. `manual-case-clang-control.txt`:

| bound | FXC | DXC | clang |
| --- | --- | --- | --- |
| `plainLiteral[10]` | ok | ok | ok |
| `swizzleOfLiteral[(10).x]` | ok | **error** | **ok** |
| `staticConstScalar[s]` | ok | ok | ok |
| `swizzleOfConstScalar[s.x]` | ok | **error** | error |
| `swizzleOfConstVector[v2.x]` | ok | **error** | error |
| `subscriptOfConstVector[v2[1]]` | ok | **error** | error |
| `constexprSwizzle[cv2.x]`, `cv2` declared `constexpr` | no `constexpr` | no `constexpr` | **ok** |

Read naively, clang's pane looks like agreement with DXC — it rejects two of the same
bounds. It is not. Clang accepts **the exact case this issue was filed about**, `[(10).x]`;
`staticConstScalar[s]` is the control that proves clang is not simply refusing
`static const`; and clang's own notes name the reason for the two it does reject —
`read of non-constexpr variable 'v2' is not allowed in a constant expression` — which is the
ordinary C++ rule for a `const` object of non-integral type, not a rule about components.
Spelled `constexpr uint2`, clang compiles both, exit 0. So in clang the restriction has a
working spelling and a standard justification; in DXC it has neither.

## History

`triage.py bisect --issue 3708 --linear`: **`repro` on all 20 releases**,
v1.4.1907 (2019-07) through v1.9.2607, no invalid probes. The repro was deliberately
targeted at `ps_6_0` rather than the `ps_6_6` of comment 1 so that no release could reject
it for lacking the profile.

v1.4.1907 is the bisection floor, so `always-repro'd` means "for as long as it is possible
to check". The report's own window is nonetheless covered exactly: **v1.6.2104 shipped
2021-04-20, four days before the 2021-04-24 report, and reproduces.** The
non-bisectable v1.5.2003 was not run, because the 2019-07→2020-10 catalog gap it fills is
nowhere near this issue's date and v1.6.2104 already brackets it.

The source dating above puts the behaviour at the 2016 initial commit, i.e. before any
probeable release, so the release scan is consistent with it having never worked.

## Assessment

Everything the issue reports is true and current. Two things it does not say:

1. the rule is not about array lengths, it is about integral constant expressions
   generally — so the fix is wider than the body implies;
2. the tested scalar-alias workaround fails, supporting the reporter's portability concern.

The remaining question is a language decision, and this triage should not pre-empt it:
should HLSL fold a component access on a constant vector/matrix into a constant expression?
FXC does. Clang does, given `constexpr`, which HLSL has no spelling for. DXC's own test
comment says it would be desirable. But it is asserted by a `-verify` test, no maintainer has
stated a position beyond llvm-beanz's 2024 *"it isn't on our priority list"*, and choosing
between "match FXC" and "adopt clang's constexpr rule" is exactly the kind of call that
belongs to the HLSL language design process rather than to a triage pass.

The suggested action is nevertheless `still-valid-keep-open` and not
`needs-human-judgement`. Nothing about the *triage* is unresolved — the behaviour is
measured, dated, located in source and confirmed on every probeable release. A maintainer
already has the relevant information and has already stated a priority position. What is
outstanding is the fix, which is true of every open bug; treating "needs a design decision to
close" as "needs judgement to triage" would put it in a tier reserved for issues the
compiler could not answer.

Worth flagging for whoever picks it up: a fix must also cover `case` labels, enumerators,
non-type template arguments and `[numthreads]`, and must update
`tools/clang/test/SemaHLSL/const-expr.hlsl`.

Comment 2 (devshgraphicsprogramming, 2024-05-16) says this *"Affects #6144 in a tangential
way"*. That relationship was not investigated; it is a cross-issue claim and belongs to
collation.

## Evidence in this directory

| file | what it shows |
| --- | --- |
| `expected.md` | the symptom, written before anything was run |
| `repro.hlsl`, `cmd.txt` | the body's minimal case, `-T ps_6_0 -E main` |
| `match.json` | `contains "error: variable length arrays are not supported in HLSL"` |
| `out-main-debug.txt` | ground truth reproduces |
| `out-v1.*.txt` | 20 releases, all `repro` |
| `variant-control-literal-*` | `int array[10]` compiles clean — predicate control, `--expect no-match` |
| `variant-nonarray-ice-*` | three non-array ICE contexts fail with *other* diagnostics — the discriminating control, `--expect no-match` |
| `variant-matrix-*` | comment 1's six-case matrix, reproducing his annotation exactly |
| `variant-operand-shapes-*` | which operand shapes are refused, including matrices and the failed workaround |
| `variant-array-contexts-*` | global / `groupshared` / struct / `cbuffer` bounds and `[numthreads]` |
| `variant-hv2018-*`, `variant-hv2021-*` | unaffected by `-HV` |
| `variant-ice-fxc-portable-*` | the source FXC compiles clean and DXC gives 3 errors on |
| `manual-case-fxc.txt` + `run-fxc-3708.py` | FXC vs DXC on the same five source files, re-derivable |
| `manual-case-clang-control.txt` + `run-ce-control-3708.py` | the clang control that changed the reading, and the `constexpr` probe |
| `manual-case-godbolt-verify.txt` | the four published panes, in full |
| `godbolt-compute.hlsl`, `godbolt-note.txt` | the published compute restating and its banner |
