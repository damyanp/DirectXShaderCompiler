# 5293 — expected symptom

Written **before** any compiler was run on the repro, per the skill's step 2.

Issue: "Assert in `template` + `out` functions when it has local variables",
filed 2023-06-14 by MarijnS95. Open. Label: `bug`.

## What the thread reports

Three separate parties, over three years, describing what they believe is one defect:

| when | who | what they report |
| --- | --- | --- |
| 2023-06-14 | reporter (body) | assert-enabled build: `Assertion 'idx.hasValue()' failed` at `tools/clang/lib/Analysis/UninitializedValues.cpp:232`, in `CFGBlockValues::operator[]` |
| 2023-06-23 | maintainer comment | "the assert is revealing a bug, but it isn't a bug that prevents correct code generation … with asserts disabled the shader compiles to correct output" |
| 2024-05-20 | Frostbite | with the assert compiled out, `idx.getValue()` on a valueless `Optional` yields uninitialised memory, which then indexes `scratch` → out-of-bounds. "in very simple situations you get away with it … in our case it just crashes" |
| 2024-09-03 | repository owner | "Confirmed that the example in the description still hits this assert." |
| 2026-08-10 | Asobo | "We're crashing in Release and hit a LLVM assert in debug … It is also templated code with out variable … **it was not crashing before**" |

So the issue carries **two claimed manifestations of one defect**:

- **Debug / assertions-enabled:** the `assert(idx.hasValue())` fires.
- **Release / `NDEBUG`:** the unchecked `Optional` is read anyway and the garbage index
  reaches `scratch[...]`, so the observable outcome is *input-dependent and possibly
  nondeterministic* — an access violation on some inputs, a wrong uninitialised-variable
  analysis on others, and apparently nothing at all on small ones.

## What "this reproduces" means

**Primary (`repro.hlsl`, verbatim from the description, command verbatim from the
description):** dxc fails **internally** — it does not return a clean diagnosed error.
On the Debug ground-truth build that is expected to be the assert, arriving either as a
trapped breakpoint (`0x80000003`) or as an LLVM assert exception (`0xE0000001`), with
`Assertion` / `assert(` text naming `UninitializedValues.cpp` and `idx.hasValue()`.

**Secondary (`repro-asobo.hlsl`, the 2026-08-10 comment's `TRayVsAABB`):** the same
internal failure. The comment gives a function body only, so an entry point and an
instantiation have to be supplied; that wrapper is agent-constructed and the file is
labelled as such.

Predicate: **`internal_failure`**, deliberately *not* a match on the assert message.
The identical defect is a trapped assert in a Debug build and an access violation (or a
stray `llvm::cast<>` `E_FAIL`) in a Release build, so message matching would score every
shipped release clean and manufacture a "fixed" verdict. The two claimed manifestations
are exactly the case the skill documents for `internal_failure` / `any_of`.

**Not a reproduction:**

- exit `0x80004005` (E_FAIL) with an ordinary `error:` line and no internal marker — that is
  a diagnosed compile error, not a crash;
- exit 0 with valid DXIL;
- `error: unrecognized ... -HV 2021` or any "templates are not supported" style rejection on
  an old release — that release never reached the code under test and is an **invalid probe**,
  not evidence of a fix. HLSL 2021 templates postdate the bisection floor (v1.4.1907), so the
  old end of the release range is expected to be unprobeable and must be *shown* to be, with
  a feature-presence control, not assumed.

## What I expect to be hard here, and how it will be decided

1. **Release binaries are Release builds.** Asserts are compiled out of all 20 catalogued
   stable releases, so a clean release sweep is *not by itself* a fix (the `#2191` shape).
   The discriminator the skill mandates: read what the unchecked value does next under
   `NDEBUG`. Frostbite already did that reading in-thread; I will confirm it against
   `UninitializedValues.cpp` and `Optional.h` in the ground-truth tree and report the release
   history as meaningful or as "silent by construction" accordingly.
2. **"It was not crashing before" is a regression claim** and it is about *Release*. It is
   answered by scanning the release binaries, linearly (endpoint agreement proves nothing
   about the middle), on **both** repros — not by the Debug build.
3. **The Release symptom is an uninitialised read**, so a single clean run is weak evidence.
   Where a release is clean I will consider `--repeat` before calling it clean.
4. The description's repro and the 2026 snippet may not behave identically. They are kept as
   separate files and every result below says which one it refers to.

## Repro quality

`complete` — the description carries a self-contained shader and the exact command line.
The 2026-08-10 snippet is `partial` on its own (function body, no entry point) and is
carried as a separate, clearly labelled secondary file.

## Prediction registered in advance

I expect the Debug ground-truth build to assert on `repro.hlsl` (the repository owner said
so in 2024 and nothing in the thread claims a fix landed). I do **not** know whether any
Release build crashes on either of these small repros; the thread says small cases often
survive. If no release crashes on either, the honest verdict is that the release history
cannot see this defect, **not** that releases are unaffected.
