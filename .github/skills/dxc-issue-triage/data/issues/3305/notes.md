# #3305 — Empty Payload struct not recognized in DXIL — triage notes

Ground truth: `main-debug`, `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433
(triage, ab5400907)`, commit `ab5400907`, Debug build. Version string verified before any
probe was run.

## Verdict in one line

**Reproduces, unchanged, on every build that can be measured** — 20 releases from v1.4.1907
(2019-07) to v1.9.2607, plus `main`. The reported backend disagreement is intact: DXIL rejects
an empty payload struct, SPIR-V compiles it.

## What was run

`cmd.txt` holds **two invocations of the same source**, because the reported symptom *is* the
difference between them:

```
-T lib_6_3 repro.hlsl
-T lib_6_3 -spirv -fspv-target-env=vulkan1.2 repro.hlsl
```

`lib_6_3` is the oldest profile that can express `[shader("miss")]`, chosen to keep old
releases probeable (SKILL.md step 6). The reporter gave no command line; see `cmd-as-filed.txt`
for the literal reading and why `-fspv-target-env` had to be added — SPIR-V raytracing is gated
on the target environment in *every* release in range, so a bare `-spirv` measures that gate
and never reaches the payload. That is the forwards-in-time invalid-probe trap, and the bare
form is captured anyway as `variant-spirv-default-env-main-debug.txt`.

## Ground truth (`out-main-debug.txt`)

```
$ dxc -T lib_6_3 repro.hlsl                     exit 0x80004005 (E_FAIL)
repro.hlsl:2:23: error: shader must include inout payload structure parameter.
[shader("miss")] void main(inout Payload payload) {}
                      ^

$ dxc -T lib_6_3 -spirv -fspv-target-env=vulkan1.2 repro.hlsl    exit 0
    %Payload = OpTypeStruct
%_ptr_IncomingRayPayloadKHR_Payload = OpTypePointer IncomingRayPayloadKHR %Payload
```

`0x80004005` is E_FAIL, which is what dxc returns for **any** ordinary diagnosed error. This is
**not** an internal failure: no assert, no access violation, no `llvm::cast` message. The
predicate therefore keys on the diagnostic text, not on the exit code (see `match.json`).

The SPIR-V module was validated: `SpirvEmitter.cpp:1036` runs spirv-val unless
`spirvOptions.disableValidation`, which defaults false and is only set by `-Vd`
(`dxcompilerobj.cpp:947`, `SPIRVOptions.h:52`). `-Vd` was not passed, so the zero-member
`OpTypeStruct` payload is not merely emitted, it passes the SPIR-V validator.

## The DXIL error is wrong about its own cause

The message says the shader must *include* an inout payload structure parameter. The shader
does include one. What the compiler actually checked is the payload's **size**:

`tools/clang/lib/CodeGen/CGHLSLMS.cpp:2480-2502`

```cpp
    case DXIL::ShaderKind::Miss:
      bNeedsPayload = true;
      LLVM_FALLTHROUGH;
    case DXIL::ShaderKind::Callable:
      if (0 == funcProps->ShaderProps.Ray.payloadSizeInBytes) {
        unsigned DiagID = bNeedsPayload
            ? ... "shader must include inout payload structure parameter."
            : ... "shader must include inout parameter structure.";
```

Three measurements pin this down:

| capture | input | result |
| --- | --- | --- |
| `out-main-debug.txt` | `struct Payload {};` | `shader must include inout payload structure parameter.` |
| `variant-nested-empty-main-debug.txt` | `struct Inner {}; struct Payload { Inner i; };` | same message — so the trigger is **size 0**, not literal emptiness of the outer struct |
| `variant-noparam-main-debug.txt` | payload parameter genuinely absent | a different, **accurate** message from Sema: `incorrect number of entry parameters for raytracing stage 'miss': 0 parameter(s) provided, expected one payload parameter` |

The caret is also on the entry function name (`repro.hlsl:2:23` is `main`), not on the payload
parameter or on the empty struct.

### The message used to be true, and stopped being true in 2023

`variant-noparam-v1.7.2212.txt` (pre) and `variant-noparam-v1.7.2308.txt` (post) bracket
PR #5131 (`f90af4e15`, 2023-04-14, "Move some of the raytracing diags to Sema"):

- **v1.7.2212**: the no-parameter shader produces *exactly* the message under test. Its
  declared expectation was corrected from `no-match` to `match` with `triage.py expect` — the
  match is the finding, not a predicate failure.
- **v1.7.2308**: the same input produces the Sema message instead.

That PR also deleted the tests that had asserted this message for the missing-parameter case
(`raytracing_miss_no_payload.hlsl`, `raytracing_closesthit_no_payload.hlsl`,
`raytracing_anyhit_no_payload.hlsl`). Measured on `miss`: since then, the codegen message
survives describing an input it no longer sees, and the only way to reach it at that stage is
the zero-sized payload — the one case the words do not describe.

## Release history (`bisect --linear`, all 20 releases, no invalid probes)

`always-repro'd across v1.4.1907..v1.9.2607`. Every release prints the identical DXIL message at
the identical location. The bug predates the report (2020-12-07): v1.5.2010, the release current
when it was filed, behaves exactly as `main` does.

The SPIR-V half, read out of the same 20 captures: **19 of 20 releases compile it**, from
v1.5.2010 onward. v1.4.1907 answers `SPIR-V CodeGen not available` — that is a feature-absence
marker, and it is why `match.json` is a positive match on the DXIL diagnostic alone. Had SPIR-V
success been part of the predicate, v1.4.1907 would have scored `no-repro` and been demoted to
`invalid-probe`, discarding a perfectly good DXIL result. Its DXIL half is valid and reproduces.

**Profile floor, confirmed rather than assumed.** `variant-control-dxil-only-v1.4.1907.txt` runs
`-T lib_6_3 control-nonempty-payload.hlsl` at the oldest release: exit 0, DXIL emitted. So
`lib_6_3`, `[shader("miss")]` and an inout payload all exist at the floor, and the repro's
rejection there is about the empty payload, not about a profile that did not exist yet. In the
event no probe was demoted — all 20 scored `repro` — but the control is what makes that
readable rather than lucky.

## Controls

| capture | input | expect | result |
| --- | --- | --- | --- |
| `variant-control-nonempty-main-debug.txt` | payload with one `float4` | `no-match` | both targets exit 0 — the predicate does not fire on a good shader |
| `variant-control-dxil-only-v1.4.1907.txt` | same, DXIL only, at the floor | `no-match` | exit 0 — feature-presence at v1.4.1907 |
| `variant-nested-empty-main-debug.txt` | payload = `{ Inner i; }`, `Inner` empty | `match` | reproduces — the check is on size |
| `variant-noparam-main-debug.txt` | no payload parameter | `no-match` | accurate Sema message instead |
| `variant-noparam-v1.7.2212.txt` | no payload parameter, pre-#5131 | `match` | the same message the empty payload gets today |
| `variant-noparam-v1.7.2308.txt` | no payload parameter, post-#5131 | `no-match` | Sema message |
| `variant-od-main-debug.txt` | repro at `-Od` | `match` | reproduces — confirms the reporter's "disabling optimizations had no effect" |
| `variant-spirv-default-env-main-debug.txt` | bare `-spirv` | `no-match` | fails on the target-env gate, not on the payload |

## Is DXC wrong to reject this?

Not established, and deliberately not asserted. Three things are known:

1. **The DXIL rejection is intentional.** `6e6f8dbdf` (2018-02-21, Tex Riddell), "Require
   payload/attribute/param structs for ray shaders. (MD CHANGE)", is where the zero-size check
   was introduced. This is not an oversight that fell out of a refactor.
2. **The SPIR-V acceptance is also deliberate enough to have passed the validator** — a
   zero-member `OpTypeStruct` is legal SPIR-V, and DXC's own spirv-val run accepts the module.
   Whether a Vulkan implementation does anything sensible with a zero-sized ray payload is a
   runtime question this triage cannot answer.
3. DXIL validation has no lower bound on payload size — `SM.RAYSHADERPAYLOADSIZE` only checks
   the declared size is not *smaller* than what the argument needs (`docs/DXIL.rst:3406`,
   `DxilValidation.cpp:5553`). The zero-size rule lives only in the front end.

So "should an empty payload be legal in DXIL?" is a **language/product decision**, not something
the compiler's current behaviour settles, and it is exactly what @damyanp asked about on
2024-04-11 — unanswered since. This triage does not pre-empt it.

What is *not* contingent on that decision: **the diagnostic is wrong either way.** If empty
payloads stay illegal, the message should say the payload is empty/zero-sized; if they become
legal, the check goes away. The current text sends the reader looking for a missing parameter
that is right there in the signature.

## Comments on the issue

Four, and the thread is worth reading before acting:

- `Jasper-Bekkers` asked for the `spirv` label; `ehsannas` declined ("it sounds like the issue
  doesn't exist when compiling to SPIR-V") and the reporter agreed. That is still correct — do
  not add `spirv`.
- `damyanp` (2024-04-11) asked which scenario needs an empty payload, calling it "an edge case
  that should work". No reply in ~2 years. That question, not the compiler, is what the issue is
  blocked on.

## Issue text

Not stale. Title and body still describe what the compiler does. One caveat a reader
reproducing today needs and the body does not carry: the SPIR-V half needs
`-fspv-target-env=vulkan1.1spirv1.4` (or `vulkan1.2`) on current DXC, or it stops at the
raytracing target-environment gate. That gate is not part of this defect — it is present in the
2020 releases too, in a different spelling (`Vulkan 1.2 is required for Raytracing`).

## Compiler Explorer

<https://godbolt.org/z/Pr3cfczY7> — two `dxc_trunk` panes over the same source, differing only
in `-spirv -fspv-target-env=vulkan1.2`. Verified through the CE API after publication:
pane 1 exits 5 with the DXIL message, pane 2 exits 0 and emits `%Payload = OpTypeStruct`.
`godbolt-note.txt` names what to compare.

No Clang pane. `hlsl_clang_trunk` rejects *both* the repro and the non-empty-payload control
with `semantic annotations must be present for all parameters of an entry function` — its HLSL
front end does not model raytracing entry points yet, so the pane would be noise about the
stage rather than evidence about the payload. Captured with its control in
`manual-case-clang-ce.txt`. `-fsyntax-only` changes nothing: the error is from Sema.

## Suggested action

`needs-human-judgement`. The compiler question is settled — this reproduces, always has, and the
two backends still disagree. What remains needs a person: (a) answer whether an empty payload
should be accepted for DXIL, and (b) independently of (a), fix a diagnostic that misnames its
own cause.

Labels: keep `bug`, add `diagnostic`. Not `spirv` — settled in-thread, and the SPIR-V path is
the one that works.
