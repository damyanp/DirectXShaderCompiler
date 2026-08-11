# #4614 — expected symptom

Written **before** running anything, from the issue text alone (SKILL.md step 2).

- **Issue:** [#4614](https://github.com/microsoft/DirectXShaderCompiler/issues/4614)
  "Assert/hang in SROA_HLSL pass related to empty base struct regression"
- **Filed:** 2022-08-24 by `simontaylor81`. Open. Label: `crash`.
- **Predecessor:** [#3016](https://github.com/microsoft/DirectXShaderCompiler/issues/3016)
  "Assert/hang in SROA_HLSL pass related to empty base struct", filed 2020-07-01,
  **closed 2021-06-24**. #4614's body says #3016 "seems to have reappeared" and the
  repro is "unchanged".

## Repro quality

`complete`. The issue body carries a self-contained HLSL source and the exact command
(`-E main -T vs_6_0`). Nothing needs reconstructing. The source is byte-for-byte the
same shader #3016 carried in 2020, which the reporter states explicitly.

## What "this reproduces" means

The title names **two** symptoms for **one** defect, and #3016's body says why they are
the same thing: *"an assert (which manifests as a hang outside of the debugger)"*.

So the symptom is: **dxc fails to compile this valid shader, by one of**

1. **hanging** — no result, unbounded. This is what a Release build (asserts compiled
   out under `NDEBUG`) does, and what the reporter observed in 2022:
   *"I just tried the exact repro listed above with the head commit as of now, and it
   hangs again"*; or
2. **failing internally** — an assert trap / access violation / LLVM fatal error. This
   is what a Debug build does, and #3016 quotes the stack:
   `SROA_Helper::RewriteBitCast` → `RewriteForScalarRepl` → `DoScalarReplacement` →
   `SROA_HLSL::performScalarRepl` → `SROA_HLSL::runOnFunction`, in
   `lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp`.

**Both count. Either alone would be wrong**, and predictably wrong in the
fix-inventing direction:

- a bare `timeout` predicate scores the **Debug** ground truth as clean, because Debug
  asserts in seconds rather than spinning;
- a bare `internal_failure` predicate scores a **Release** build as clean, because with
  the assert compiled out there is nothing to trap — the build spins instead.

Predicate must therefore be:

```json
{ "kind": "any_of", "value": [ { "kind": "timeout" }, { "kind": "internal_failure" } ] }
```

Explicitly **not** a match on the assert *message*: SKILL.md records that the message
differs between Debug and Release and between Windows and Linux, and that an internal
failure may print nothing at all. And `E_FAIL` (0x80004005) is an ordinary diagnosed
error, **not** a crash — if dxc emits a clean `error:` and exits E_FAIL, that is
`does-not-repro` or `changed-behavior`, not a reproduction.

## What "does not reproduce" would look like

dxc exits **0** having compiled the shader, emitting a `vs_6_0` DXIL module with a
`main` returning `SV_Position`. That is the only clean outcome, because the input is
valid HLSL: an empty struct nested in a base class of a derived struct, assigned to.

A third possibility exists and must not be collapsed into either bucket: dxc **rejects**
the shader with an ordinary diagnostic. That would be `changed-behavior` — the crash
would be gone but a valid shader would still not compile.

## History expectation, and why binary search is invalid here

The title says **regression** and the thread is an explicit **fix-then-reappear**:
#3016 was closed 2021-06-24, and the same shader was reported broken again 2022-08-23.
The symptom is therefore **not monotonic** over the release sequence, and
`bisect` (binary search) is unsound on it:

- binary search assumes one transition, so with a non-monotonic history it returns an
  arbitrary boundary;
- worse, `bisect` short-circuits when both endpoints agree — and if this is
  broken → fixed → broken, an *old* broken endpoint and a *new* broken endpoint agree,
  which reports `always-repro'd` and **erases the fix window in the middle** entirely.

So: **`bisect --linear`**, one probe per stable release, v1.4.1907 forward.

Predictions to be falsified by measurement, not assumed:

- releases around 2020 (the #3016 report) should reproduce;
- some release after 2021-06-24 should be clean, if #3016's fix shipped;
- some release before 2022-08-24 should be broken again, if the regression shipped;
- ground truth on `main` — unknown; the issue is open but that is not evidence.

## Hazards specific to this issue

- **`timeout` costs wall-clock on every clean release.** A clean release exits fast; a
  hanging one burns the whole timeout. A 20-release linear scan with a hang in it is
  slow by construction. That is a cost, not a reason to drop the clause.
- **`invalid-probe`:** `vs_6_0` is ancient and this shader uses no post-2019 feature,
  so every release from the v1.4.1907 floor should be able to express it. If any
  release rejects it, check whether the rejection is about the feature or about the
  repro before letting `bisect` trim it.
- **NDEBUG:** SKILL.md warns that an assert-only defect is invisible in release builds
  ("silent by construction"). That warning must **not** be applied reflexively here:
  #3016 states the release manifestation is a *hang*, which is loud and observable. The
  `timeout` clause is exactly what makes releases measurable. Whether the release
  builds actually hang is a measurement to make, not an assumption.
- The reporter says he does not know when it regressed:
  *"I'm afraid I don't have any information as to when it might have regressed."*
  So the release history is the contribution this triage can make.
