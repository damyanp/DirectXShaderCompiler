# #2331 — Problem with DXIL signing and switch case/enum use

Written **before** any compiler was run, from the issue text alone
(`issue.json`, fetched 2026-08-06). Filed 2019-07-11 by @LautrecOfCarim.

## What the issue reports

A pixel shader switches on an `enum class`-typed value, supplies a `case` for **every**
enumerator, and supplies **no `default:`** — so control flow can fall off the end of a
non-`void` function. The reporter says the compile fails:

```
warning: DXIL.dll not found.  Resulting DXIL will not be signed for use in release environments.

error: validation errors
at 0x24f9e5b2a10 inside block #0 of function MainPS Instructions must be of an allowed type

Validation failed.
```

The entry point is `MainPS()` returning `float4 : SV_Target0`, and the shader uses
`ConstantBuffer<T>`, so the target is `ps_6_0` and the entry `MainPS`. No command line is
given in the report (it was produced on shader-playground), so the target/entry are
**inferred**, and no `-Vd` or other flag is mentioned anywhere in the thread.

### Three further claims in the body

| # | claim |
| --- | --- |
| **B1** | commenting out **any one** of the three cases → DXIL validates clean ("but it shouldn't, because there is no default case") |
| **B2** | adding a fourth enumerator (`Fake`) → still fails validation, but with a "correct error message" |
| **B3** | adding a `default:` case → compiles clean |

### What the comments add

* **@tristanlabelle** (contributor, 2019-07-17) diagnoses it: clang emits an LLVM
  `unreachable` for the fall-off-the-end path, and `unreachable` **is not a legal DXIL
  instruction**, which is what the validator is complaining about. He adds that a two-case
  switch gets lowered to if/then/else during initial codegen (hence B1), that the "not all
  cases handled" warning is unreliable, and that falling off the end of a non-void function
  ought to be a **Sema error** rather than a validator error. He explicitly rejects the
  reporter's closing remark: a `default:` on an exhaustive enum switch is legitimate, because
  nothing constrains an enum-typed value to the declared enumerators.
* **@LautrecOfCarim** (2019-07-26) accepts the workaround: always write a `default:`.
* **@damyanp** (member, 2024-06-12): "We aren't expecting to fix this in dxc."
* **@llvm-beanz** (collaborator, 2024-06-21): "I think we can mark this dormant for DXC.
  I've filed an issue to remove these instructions during DXIL lowering in Clang."

So the maintainers' position since 2024 is **won't-fix in DXC, handled in Clang**. Nothing in
the thread claims it was ever fixed.

## What "this reproduces" means

Ground truth reproduces the issue iff, on `repro.hlsl` compiled as `-T ps_6_0 -E MainPS`:

1. the compile **fails**, and
2. the failure is a **DXIL validation error** naming the rule
   `Instructions must be of an allowed type`.

Both parts matter. A validation failure exits **E_FAIL (0x80004005)** — that is an ordinary
diagnosed error, **not** an internal failure, and must not be classified as a crash. If the
symptom instead turns out to be a crash/assert, that is a *different* symptom and needs its
own `internal_failure` predicate rather than a text match.

Not the symptom:
* the `DXIL.dll not found` warning on its own. That warning is about **signing**, and it is a
  property of the reporter's environment (shader-playground shipped no `dxil.dll`), not of
  the bug. Validation still runs without it, via the validator built into `dxcompiler.dll`.
* a clean compile that merely produces bad code — the reported symptom is a hard failure.

## Signing, and what it can do to this measurement

The title says "signing", but the quoted output shows validation failing and signing being
*skipped* — so the title's framing is the reporter's inference. Two environmental hazards
that could invent or erase a result, to be established and recorded rather than assumed:

* whether a `dxil.dll` sits next to the `dxc.exe` under test, for **ground truth and every
  release probed**. Absent, output is unsigned and a warning is printed; present, the
  external validator is used, and its version — not the compiler's — decides the wording of
  a validation diagnostic. A history where half the releases had no validator is worthless.
* `-Vd` disables validation and therefore signing. Nothing in the report uses it; if it is
  used at all here it is as a deliberately-labelled variant, never in `cmd.txt`.

## Predictions (recorded so they can be wrong)

* the compile fails with that validator rule text, on ground truth and on every release back
  to the v1.4.1907 floor — nothing in the thread suggests a fix, and 2024 maintainer comments
  say none is planned;
* B3 (default case) holds — that is the control the predicate must **not** match;
* B1 and B2 are the claims most likely to have moved since 2019, since both depend on how the
  front end lowers a switch.

Risks to the history: `enum class` may predate v1.4.1907's front end, and today's default
`-HV 2021` differs from the 2019 default — either would produce `invalid-probe`s rather than
results. A minimal `enum class` feature-presence control settles which.

## Repro quality

**complete** — the body supplies a self-contained shader that compiles as-is once the
(inferable) target and entry point are supplied.
