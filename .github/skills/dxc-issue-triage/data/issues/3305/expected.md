# #3305 — Empty Payload struct not recognized in DXIL

*Written before running any compiler.*

Filed 2020-12-07 by `Jasper-Bekkers`. Label: `bug`.
<https://github.com/microsoft/DirectXShaderCompiler/issues/3305>

## What the issue claims

The complete repro is in the body:

```hlsl
struct Payload {};
[shader("miss")] void main(inout Payload payload) {}
```

> When compiling an RT shader to Spir-v, the empty Payload struct is recognized — and the
> shader compiles just fine, however with DXIL the same shader fails to compile.
> I've tried disabling optimizations, however this did not have any effect.

So the report is **not** "DXC fails". It is a **disagreement between DXC's own two backends**
on one input: `-spirv` succeeds, DXIL does not. That is the whole claim, and a probe of only
one target measures half of it.

The body links a third-party shader playground page. That is context, not evidence; the
evidence here is what is run locally.

## What the thread adds

Four comments, and none of them is a repro or a workaround:

- 2021-01-17 `Jasper-Bekkers` asks for the `spirv` label; 2021-01-18 `ehsannas` (contributor)
  declines — "it sounds like the issue doesn't exist when compiling to SPIR-V" — and the
  reporter agrees. So the `spirv` label is **already settled as wrong** for this issue, and
  proposing it would re-open a question the thread closed.
- 2024-04-11 `damyanp` (member): *"To help us prioritize this, can you explain the scenarios
  that this is blocking a bit please? It does indeed seem like an edge case that should work,
  we'd just like to understand when you'd need to have an empty payload?"* — unanswered since.

That last comment is the closest thing to a maintainer position: an inclination that it
*should* work, explicitly not a decision, and a request for justification that never came.

## Neither the body nor the thread quotes the DXIL error

Nothing on the issue says *how* the DXIL compile fails — no message, no exit code. So the
symptom has to be stated in terms of the observable difference, and the predicate anchored to
whatever DXC actually prints, read from the capture rather than guessed at. Recorded in
advance so that "the error looked reasonable" cannot be back-fitted later.

## What "this reproduces" means

Compiling the two-line shader above at a raytracing-capable library profile, twice from the
same source:

1. **DXIL** (`-T lib_6_3 repro.hlsl`) — the compile **fails**: it does not produce a DXIL
   module, and says so with an error; **and**
2. **SPIR-V** (`-T lib_6_3 -spirv repro.hlsl`) — the same source **succeeds** and emits a
   SPIR-V module.

Both halves are required. DXIL failing on its own is only half the report; SPIR-V succeeding
on its own is not a defect at all.

The predicate will key on **the DXIL failure specifically**, and must not be satisfiable by
anything in the SPIR-V half of the same capture — the two invocations land in one output file,
so a loose pattern could match SPIR-V disassembly or a SPIR-V-side diagnostic and score a
reproduction that measured nothing.

## What would count as **not** reproducing

- DXIL compiles the empty payload successfully (with or without a warning). That is the
  "fixed" shape — the backends then agree in the direction the reporter wanted.
- **Both** backends reject it. That is also *not* this issue: the disagreement is gone, the
  input is simply rejected, and the remaining question ("should an empty payload be legal?")
  is a language question, not this bug. Record it as `changed-behavior`.

## What is explicitly **not** the symptom

- **A non-zero exit code.** On Windows dxc returns `E_FAIL` (0x80004005) for every ordinary
  diagnosed error, so exit status alone carries no information here, and a "nonzero exit"
  predicate would score a plain syntax error identically.
- **An internal failure / crash.** Nothing in the issue reports one. If ground truth turns out
  to assert or access-violate, that is a *different and worse* symptom than what was filed and
  needs its own `internal_failure` predicate and its own history, not a re-reading of this one.

## The question this triage must answer, but the predicate cannot

Whether an empty payload *should* compile is not obvious, and the issue assumes it without
argument. A DXR payload has a size; the runtime reserves that many bytes per ray. Zero-sized
structs are legal in SPIR-V/Vulkan-flavoured rules in a way they may not be in DXIL, where
every struct carries a type annotation and a size. So there are three genuinely different
outcomes to distinguish, and only the first is a plain compiler defect:

1. DXIL rejects it for no good reason and the diagnostic is poor → defect.
2. DXIL rejects it deliberately, but the *message* is unhelpful, mislocated or misleading →
   still a real, narrower finding: a diagnostic-quality defect, not a codegen one.
3. DXIL rejects it correctly and SPIR-V is the lenient/wrong one → the fix, if any, belongs on
   the SPIR-V side, and the issue as written points at the wrong backend.

So: read the diagnostic and judge whether it is a *good* one, and say plainly where the answer
needs a product/language decision rather than pre-empting it.

## Repro quality

`complete` — the body supplies a self-contained two-line shader that compiles as-is. Only the
target profile had to be supplied, and `[shader("miss")]` fixes it to a library profile
(`lib_6_3` or later, DXR 1.0); no entry point flag is needed for a lib target.

## Known hazards, recorded in advance

- **Profile floor.** `lib_6_3` did not always exist. Any release predating it will answer
  `invalid profile` and measure nothing — an `invalid-probe`, not a fix. Do not take the
  runner's classification on trust: confirm it with a **feature-presence control** (the same
  shader with a *non-empty* payload, same profile and flags). Both rejected ⇒ the release
  predates the feature. Control clean but repro rejected ⇒ the rejection is about the empty
  payload and is real evidence.
- **SPIR-V raises the floor further.** v1.4.1907 answers `SPIR-V CodeGen not available`, which
  is itself a feature-absence marker. Because both invocations share one capture, that string
  will be present in the oldest probes even when the DXIL half ran perfectly well. The
  predicate must therefore be a *positive* match on the DXIL error, so those probes still score
  `repro` on the strength of the DXIL half rather than being demoted for the SPIR-V half. Check
  the header of every old probe rather than assuming this held.
- **The symptom is a diagnostic**, so the runner's feature-absence markers and the symptom are
  the same kind of observation (SKILL.md step 6). Write the diagnostic verbatim into
  `match.json`, and re-read every `invalid-probe` classification against the captured text.
- **`-HV` moved to 2021 in v1.7.2308.** The repro uses no language feature affected by it, but
  if old and new releases disagree, check that before calling it a transition.
