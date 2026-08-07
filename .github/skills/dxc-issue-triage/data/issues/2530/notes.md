# #2530 — Array bound with static const variable — triage notes

## Verdict

**Still reproduces**, exactly as filed, on every release that can be checked and
on `main`. The issue text is accurate in every particular, including the quoted
diagnostic and the claim about FXC.

| | |
| --- | --- |
| ground truth | `main-debug` @ `ab5400907` — `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` |
| status | `repros` |
| repro quality | `complete` |
| history | `always-repro'd` (v1.4.1907 → v1.9.2607, all 20 releases, `--linear`) |
| text stale | no |
| suggested action | `still-valid-keep-open` |
| Compiler Explorer | https://godbolt.org/z/Yzd9KjcaG |

## What was tested

`repro.hlsl` is case 1 of the issue body verbatim; `case2.hlsl` is case 2
verbatim. The reporter names no profile, no flags and no compiler version.
`SV_Target` fixes the stage as pixel, so `cmd.txt` is:

```
-T ps_6_0 -E main repro.hlsl
```

`ps_6_0` rather than a newer profile so that every release back to the
v1.4.1907 floor actually compiles the repro (SKILL.md step 6) — and all 20 did.

Predicate (`match.json`): `contains "variable length arrays are not supported in
HLSL"`, the exact string quoted in the issue. Positive rather than absence-based,
so a release that failed to parse the repro could not satisfy it for free.
Deliberately not `nonzero_exit`: dxc returns E_FAIL for every diagnosed error on
Windows, so `nonzero_exit` would have scored the boundary probes below —
which fail for a *different* reason — as this bug.

## Results

| capture | result |
| --- | --- |
| `out-main-debug.txt` | `repro` — exit 0x80004005, `repro.hlsl:7:16: error: variable length arrays are not supported in HLSL` |
| `variant-case2-main-debug.txt` | `repro`, `--expect match` — issue case 2, same diagnostic at `case2.hlsl:9:16` |
| `variant-control-uint-bound-main-debug.txt` | `no-repro`, `--expect no-match` — negative control, exit 0, DXIL emitted |
| `variant-hv2016-main-debug.txt` | `repro`, `--expect match` — `-HV 2016` |
| `variant-boundary-float-literal-main-debug.txt` | `no-repro`, `--expect no-match` — `float array[uint(1.0f)]`, exit 0 |
| `variant-boundary-implicit-conv-main-debug.txt` | `no-repro`, `--expect no-match` — different diagnostic, see below |
| `out-v1.4.1907.txt` … `out-v1.9.2607.txt` | `repro` — 20 of 20 releases (case 1) |
| `variant-case2-v1.4.1907.txt`, `variant-case2-v1.9.2607.txt` | `repro`, `--expect match` — case 2 at both release endpoints |
| `manual-case-ce-fxc.txt` | FXC 10.1 compiles **both** cases, exit 0 |
| `manual-case-ce-clang.txt` | clang HLSL front end rejects both cases; control clean |

The negative control matters: `control-uint-bound.hlsl` is byte-identical to
`repro.hlsl` except that `ARRAY_SIZE` is `static const uint` and the cast is
gone. It compiles and emits DXIL, so the predicate is not firing on "an array
with a named bound" — it is firing on the conversion.

### The language-version trap does not apply

SKILL.md step 6 warns that a repro filed before the `-HV` default moved to 2021
can be rejected by a *newer* compiler for a new reason, faking a fix. Checked
directly: `-HV 2016` produces the identical diagnostic
(`variant-hv2016-main-debug.txt`). Language version is not a factor here, and the
predicate is a positive match on the reported text rather than a bare failure,
so a hypothetical new rejection could not have masqueraded as this one anyway.

## Root cause, from source

The construct is **an array bound that is a compile-time constant reached
through a float→integer conversion**. The path is entirely in `Sema`, before any
codegen:

1. `Sema::BuildArrayType` — `tools/clang/lib/Sema/SemaType.cpp:1978`
2. → `isArraySizeVLA` — `SemaType.cpp:1943`, which calls
   `Sema::VerifyIntegerConstantExpression`
3. → `CheckICE` — `tools/clang/lib/AST/ExprConstant.cpp:9016`, C++03
   integer-constant-expression rules
4. non-ICE ⇒ `Context.getVariableArrayType(...)` at `SemaType.cpp:2098`
5. ⇒ the HLSL-specific check at `SemaType.cpp:2142-2146` emits
   `diag::err_hlsl_vla` (`DiagnosticSemaKinds.td:7726`)

The two reported cases fail at two *different* points inside `CheckICE`:

- **Case 1**, `uint(ARRAY_SIZE)`: the cast cases at `ExprConstant.cpp:9308-9344`.
  An explicit cast is an ICE only when its operand is a `FloatingLiteral`
  (line 9317-9318); a `CK_FloatingToIntegral` applied to a `DeclRefExpr` falls
  through to `default: return ICEDiag(IK_NotICE, ...)` at line 9343.
- **Case 2**, `static const uint N = (uint)ARRAY_SIZE;`: `Expr::DeclRefExprClass`
  at `ExprConstant.cpp:9142-9172`. A const integral variable is an ICE only if
  `VD->checkInitIsICE()` (line 9171), and N's initializer is case 1's cast — so
  the failure propagates one level out.

This predicts the boundary exactly, and the boundary probes confirm it:
`float array[uint(1.0f)]` compiles (operand *is* a `FloatingLiteral`), and
`static const uint ARRAY_SIZE = 1` compiles (no conversion at all).

Note the HLSL-specific code at `SemaType.cpp:2142` is only the *reporting* of
the condition. What decides it is stock clang C++03 ICE evaluation, which HLSL
inherited. Nothing in that path is HLSL-aware.

### An adjacent case that is *not* this issue

`boundary-implicit-conv.hlsl` drops the explicit cast — `float array[ARRAY_SIZE]`
with `ARRAY_SIZE` still `static const float`. That never reaches the VLA path at
all: HLSL's LangOpts are C++ but not C++11, so `SemaType.cpp:2068-2074` rejects
it earlier with

```
error: size of array has non-integer type 'float'
```

Different diagnostic, different code path, so it is outside this issue as filed.
It is recorded because it was predicted to behave like the repro and did not —
the declared `--expect` was revised `match` → `no-match` with `triage.py expect`,
which leaves the measurement untouched.

## Cross-compiler

**FXC** (`fxc_10_0_19041` on Compiler Explorer, `/T ps_5_0 /E main`) compiles
both cases and emits `ps_5_0` code — 2 instruction slots, `mov o0.xyzw,
l(0,0,0,0)`. The `fxc-disagrees` label and the reporter's 2019 claim are both
verified, not assumed. FXC supports only shader model 5.x, hence `ps_5_0`; that
is the only difference from the DXC probes.

**clang's HLSL front end** (`hlsl_clang_trunk`) rejects both cases too, but says
why:

```
<source>:7:22: note: read of non-constexpr variable 'ARRAY_SIZE' is not allowed in a constant expression
<source>:7:16: error: variable length arrays are not supported for the current target
```

and for case 2:

```
<source>:9:17: note: initializer of 'ARRAY_SIZE_UINT' is not a constant expression
```

Those notes are an independent statement of the root cause derived from source
above, from a compiler that shares the ancestry but not the code.

**The clang result has a control**, per SKILL.md step 7. clang's DXIL backend
cannot lower a pixel shader writing `SV_Target`, so without `-fsyntax-only`
*every* shader fails there — including `control-uint-bound.hlsl`, with
`Unsupported intrinsic llvm.dx.store.output.v4f32 for DXIL lowering`. That is
the #1702 trap exactly. With `-fsyntax-only` the control exits 0 and the repro
still errors, so the difference survives and the clang diagnostic is about the
constant expression, not the stage. All four cases are in
`manual-case-ce-clang.txt`.

## History

`bisect --linear`: **`repro` on all 20 catalogued releases**, v1.4.1907
(2019-07) through v1.9.2607, plus `main`. No `invalid-probe`, no window. That
scan uses `cmd.txt`, so it covers case 1; case 2 was probed separately at both
endpoints (`variant-case2-v1.4.1907.txt`, `variant-case2-v1.9.2607.txt`) and
fails identically there.

The plain `bisect` short-circuited after the two endpoints agreed; the linear
scan was run anyway so that "always" rests on 20 measurements rather than 2.

**v1.4.1907 is the bisection floor** — the oldest release shipping a usable
`dxc`. It postdates this report by three months, so "always reproduced" means
"for as long as it is possible to check", not "since it was filed".

## Compiler Explorer

https://godbolt.org/z/Yzd9KjcaG — four panes, verified before publishing:

| pane | args | result |
| --- | --- | --- |
| `fxc_10_0_19041` | `/T ps_5_0 /E main` | exit 0, emits `ps_5_0` |
| `dxc_1_6_2112` | `-T ps_6_0 -E main` | `error: variable length arrays are not supported in HLSL` |
| `dxc_trunk` | `-T ps_6_0 -E main` | same |
| `hlsl_clang_trunk` | `-T ps_6_0 -E main -fsyntax-only -fno-color-diagnostics` | non-constexpr note + VLA error |

`-fno-color-diagnostics` only stops CE returning ANSI escapes; it changes no
result. CE is single-file, which is no limitation here — the repro is one file.
CE runs Release builds, also no limitation: the symptom is a front-end
diagnostic, not an assert, and all 20 release binaries show it.

## Labels

Now: `bug`, `fxc-disagrees`. Both are supported by the evidence — FXC really
does accept this, measured, not quoted.

Proposed add: **`diagnostic`**. Separable from whether DXC's *behaviour* should
change: HLSL has no variable-length arrays, so nobody writing this shader
believes they wrote one, and the message names neither the conversion nor the
constant-expression rule that produced it. clang's `note:` on the same input
shows what the useful wording looks like. This stands even if the language
decision is that DXC is right to reject the code.

No removals. Nothing in the body or the single comment contradicts either
existing label. I may be missing thread history not visible in `issue.json`.

## Assessment

The report is accurate and the behaviour is unchanged after six years, so there
is nothing to close and nothing stale to correct. What triage adds is the
boundary and the mechanism: the defect is not about arrays or about `static
const`, it is that a **float→integer conversion of a named constant is not an
integer constant expression** under the C++03 ICE rules DXC inherited, while it
is one under FXC's. Whether HLSL should follow FXC is a language decision this
triage does not pre-empt; both spellings the reporter gave are one rule.

`still-valid-keep-open`, confidence high. The only thing the compiler cannot
settle is the language question, and that is a maintainer call.

## Thread

One comment (pow2clk, 2020-08-14): `Related to #2188`. No repro, no diagnosis,
no "still repros" datapoint. Per the batch's isolation rule no cross-issue
judgement is made here or in `comment.md`; see `method-notes.md`.
