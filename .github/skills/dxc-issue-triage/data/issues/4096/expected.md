# #4096 — `bool` cast operator doesn't implicitly trigger

Filed 2021-11-22 by llvm-beanz. Label at filing: `hlsl2021`; relabelled `hlsl-next`
2022-10-04; milestoned **HLSL 202x** 2023-06-30. Still open.

Written **before** any compiler was run.

## What the issue claims

A user-defined conversion operator to `bool` on a struct should make that struct usable in a
context requiring `bool` (here, an `if` condition) by implicitly invoking the operator. DXC
does not do that.

The body gives a complete compute shader:

```hlsl
struct Foo {
  int x;
  operator bool() {
    return x < 5;
  }
};

[numthreads(1, 1, 1)]
void main(uint tidx : SV_DispatchThreadId) {
  Foo A = {1};
  if (A)
    A.x += 2;
}
```

No command line, no DXC version, and no observed diagnostic are given — only "This currently
does not work."

## Repro quality

`complete` — the body is a whole shader with an entry point and `[numthreads]`, so
`-T cs_6_0 -E main` follows from the source. Two gaps the reporter left, both recorded here so
they cannot later be rationalised:

1. **No language version.** Member `operator` declarations are an HLSL 2021 feature (see
   #5103's body: "The cast operator syntax was enabled for HLSL 2021"). In 2021-11 the default
   was HLSL 2018, so the reporter must have been on `-HV 2021` or on a build whose default had
   already moved. `cmd.txt` will pin `-HV 2021` explicitly so that every compiler in a release
   sweep is asked the same question, and so releases predating HLSL 2021 announce themselves
   (`Unknown HLSL version: 2021`) instead of failing with an unrelated parse error.
2. **The shader has no observable.** `A.x += 2` writes a local that nothing reads, so the
   emitted DXIL cannot show *which* conversion the compiler chose. The reporter's shader can
   answer "is this accepted, and how", but not "was the operator body executed". A
   discriminating shader is therefore needed as an auxiliary case and will be labelled
   `agent-constructed`.

## What "this reproduces" means

**Reproduces** = DXC does not implicitly invoke the user-defined `operator bool()` when the
struct appears in a `bool` context. Predicted observable forms, any of which is the symptom:

* **(A) rejected condition** — the `if (A)` conversion is diagnosed (e.g. "no viable
  conversion"), i.e. the operator is not considered;
* **(B) silently substituted conversion** — the shader compiles, but the branch condition is
  HLSL's flat/element-wise conversion of `Foo` rather than the value of `x < 5`. This is the
  form #5103 (2023-03-17) and #6081 (2023-11-30) describe for C-style casts;
* **(C) rejected declaration** — DXC refuses `operator bool()` at its declaration, so the
  question of implicit triggering cannot even arise. This form did not exist when the issue
  was filed; PR #8206 (commit `b13e386be`, merged 2026-04-14, closing #5103) added
  `err_hlsl_unsupported_conversion_operator` — "conversion operator overloading is not
  allowed" — and that code is present in the ground-truth tree. If ground truth shows (C),
  the reported symptom has **changed shape**, not been fixed: the requested feature is still
  absent, and the guard llvm-beanz identified
  (`SemaOverload.cpp:1136`, `if (SuppressUserConversions || S.getLangOpts().HLSL)`) is still
  in the tree at `13730886e`.

**Does not reproduce** = the shader compiles *and* the emitted DXIL shows the branch condition
derived from the operator body (`x < 5`), i.e. changing the operator's expression changes the
generated code. Nothing less counts: a clean exit alone cannot distinguish (B) from a fix,
because with `x == 1` both `x < 5` and a flat `bool(x)` conversion are `true`.

**Not a fix, and must not be recorded as one:** form (C). Refusing to compile the construct
removes the silent-miscompile hazard but leaves the feature request open. The issue asks for
the operator to *work*, not for it to be diagnosed.

## Pre-registered predicate sketch

One defect, two signatures across time, so `match.json` will be an `any_of`:

* `contains "conversion operator overloading is not allowed"` — form (C);
* an arm covering forms (A)/(B) on releases that accept the declaration.

Arm 2 must carry a positive anchor: an absence clause alone is satisfied for free by any
release that fails to parse the input (v1.4.1907 etc. predate HLSL 2021 entirely), which would
manufacture a reproduction. Whatever arm 2 ends up matching must be a *positive* string that
only a build which accepted the declaration can emit.

## Controls planned

* **`control-no-operator.hlsl`** — the same struct with the `operator bool()` member deleted
  and `if (A.x < 5)` written out. It must compile on every build and must **not** match: this
  proves the predicate is not firing on the shader shape, the profile or the `if`.
* **`case-discriminating.hlsl`** (agent-constructed) — an `RWBuffer` output plus an operator
  whose result *disagrees* with the flat conversion (e.g. `x = 1`, `operator bool() { return
  x > 5; }`), so the generated code says which conversion was used. This is the only input
  that can falsify a "does not reproduce" claim.

## Hazards noted in advance

* This is labelled `hlsl-next` and milestoned HLSL 202x, so "does it still reproduce" may be
  the uninteresting half. The resolution trail — #5103, #6081, hlsl-specs — is where the
  useful finding is likely to be.
* An absence-shaped predicate over a repro that no longer compiles is the skill's documented
  free-reproduction trap; hence the positive-anchor requirement above.
* Releases predating HLSL 2021 are expected to be `invalid-probe`, not clean runs.
