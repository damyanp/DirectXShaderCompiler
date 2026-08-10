# Expected symptom - #3902 "error: Flags must match usage."

Written **before** running any compiler, from the issue text alone (body + all four comments).

**Repro quality: complete.** The body carries a whole shader, the exact command line and the
release tested. Two commenters add two further complete shaders. Nothing has to be invented.

## What was reported (2021-08-09, @bioglaze, "June 2021 DXC release")

A compute shader that **declares a `RayQuery<FLAGS>` object and never uses it** fails to
compile:

```
error: validation errors
error: Flags must match usage.
note: Flags declared=33554432, actual=0
Validation failed.
```

Command line as filed:

```
dxc /nologo /all_resources_bound /Ges /WX /O3 /T cs_6_6 /E computeRTAO /Fo shader.cso shader.hlsl
```

## Three reported instances, all the same shape

| # | source | stage | flags on the RayQuery | uses the object? |
| --- | --- | --- | --- | --- |
| 1 | body | `cs_6_6` | CULL_NON_OPAQUE \| SKIP_PROCEDURAL_PRIMITIVES \| ACCEPT_FIRST_HIT_AND_END_SEARCH \| CULL_BACK_FACING_TRIANGLES | no |
| 2 | @DethRaid 2021-12-02 | `ps_6_6` | ACCEPT_FIRST_HIT_AND_END_SEARCH \| SKIP_PROCEDURAL_PRIMITIVES | no |
| 3 | @DethRaid 2023-09-01 | `ps_6_6` | ACCEPT_FIRST_HIT_AND_END_SEARCH \| CULL_BACK_FACING_TRIANGLES \| SKIP_PROCEDURAL_PRIMITIVES | no - every use commented out, but an RTAS is fetched from `ResourceDescriptorHeap` |

All three report the identical error text. Instance 2 adds that SM 6.4 and 6.5 behave the
same, so the symptom is not specific to 6.6. Instance 3 adds a **control the reporter
supplies himself**: un-commenting the `TraceRayInline`/`Proceed`/`CommittedStatus` block makes
the same shader compile cleanly.

## Diagnosis offered in the thread (not yet verified here)

@DethRaid, 2023-09-01, relaying a DirectX Discord discussion: the front end records the
`RayQuery` template's flags in the shader's declared feature/flag metadata, optimisation then
dead-code-eliminates the unused object, and the **validator recomputes the flags from what is
left** and finds nothing using them. Declared != actual, so validation fails. If that is the
mechanism, `-Od` (or anything preventing DCE) may change the result, and so may `-Vd`
(validation disabled). This is a hypothesis to test, not an established fact.

## "This reproduces" means, precisely

dxc **fails the compile** of a shader that declares an unused `RayQuery<FLAGS>`, and the
combined output contains both

* `Flags must match usage.`, and
* a note of the form `Flags declared=<nonzero>, actual=0`.

Anything else is not this symptom.

## Traps this issue is shaped to walk into

* **Nonzero exit is not a crash.** DXC returns E_FAIL (0x80004005) for every ordinary
  diagnosed error, and a **DXIL validation failure is exactly that**. A `nonzero_exit` or
  `internal_failure` predicate would be wrong here in both directions. The predicate must be
  the diagnostic text.
* **The symptom IS a diagnostic**, so "this release printed an error" cannot by itself mean
  "this release could not run the repro". Every `invalid-probe` demotion in the release sweep
  has to be read out of the capture and confirmed to be a *different* rejection (unknown
  profile, `RayQuery` undeclared, etc.), not this one.
* **`RayQuery` is DXR 1.1 / SM 6.5.** Releases older than that reject the source outright and
  measure nothing. `cs_6_6` narrows it further. A feature-presence control is needed to tell
  "this release predates the feature" from "this release rejected my repro for some other
  reason".
* **Correct behaviour is a clean compile.** Declaring an object you do not use is legal HLSL.
  So `does-not-repro` here would mean "dxc now compiles this", which is the fix, not a
  regression.

## Classification rules fixed in advance

| observation | verdict |
| --- | --- |
| both anchors present, compile fails | `repros` |
| compile succeeds, exit 0 | `does-not-repro` |
| compile fails with a *different* message about the same construct (e.g. a front-end diagnostic telling the user the object is unused, or a differently-worded validator error) | `changed-behavior` |
| compile fails because the release cannot express `RayQuery`/the profile | not a result at all - `invalid-probe` |

## Controls planned (before any of them is run)

1. **Reporter-supplied negative control** - instance 3 with the ray-tracing calls
   *un-commented*. Expect `no-match`: it is the input the reporter says works, so if the
   predicate fires on it too, the predicate is not measuring this bug.
2. **Feature-presence control** - the smallest shader that mentions `RayQuery` at all, under
   the same profile and flags, run on every probed release. `invalid-probe` on both it and the
   repro means the release predates DXR 1.1; a clean control beside a rejected repro means the
   rejection is about the repro and must not be trimmed from the history.
3. **Flag-set control** - the same shader with `RayQuery<>` (no flags). Declared flags are then
   zero, so declared == actual == 0 and it must compile. Expect `no-match`. This is what
   isolates "declared flags that nothing uses" from "unused RayQuery" in general.
