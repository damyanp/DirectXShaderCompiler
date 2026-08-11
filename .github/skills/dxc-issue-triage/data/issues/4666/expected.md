# Issue 4666 — "Variable has incomplete type 'SamplerState [2]'"

Filed 2022-09-16 by `TheMostDiligent` against commit `42eb79311e1c7f4ce6e110ec631243708664133b`.
Labels at fetch time: `bug`, `spirv`. Two comments: a collaborator minimal repro
(`llvm-beanz`, 2024-08-05, https://godbolt.org/z/39Khq117f) and a maintainer
acknowledgement (`damyanp`, 2024-08-05: *"Ack that this is a bug, however current priority
has this as Dormant."*).

**Written before any compiler was run.** Everything below is derived from the issue text and
from the collaborator's linked reproduction, not from observed output.

## What the reporter says

A function that takes a resource array plus a **sampler array**:

```hlsl
... Reflection(Texture2D<float4> Textures[4],
               SamplerState Samplers[2],
               ...
```

"used to work just fine", but at the named commit fails with:

```
hlsl.hlsl:175:42: error: variable has incomplete type 'SamplerState [2]'
                            SamplerState Samplers[2],
                                         ^
```

The collaborator's linked reproduction reduces this to a single line compiled with
`-T lib_6_6`:

```hlsl
void Reflection(Texture2D<float4> Textures[4], SamplerState Samplers[2]) {}
```

Three further claims are in the body, and each is a separately checkable ask:

1. **Struct workaround fixes DXIL.** Wrapping the samplers in a struct and passing the struct
   compiles for DXIL.
2. **Struct workaround breaks SPIR-V.** The same struct form, compiled with `-spirv`, fails:
   ```
   fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-None-04667] In Vulkan,
   OpTypeStruct must not contain an opaque type.
     %Test = OpTypeStruct %_arr_type_sampler_uint_2
   ```
3. **Merely declaring the struct makes the bare sampler-array parameter work.** With
   `struct Resources { SamplerState Samplers[2]; };` present anywhere before the function, the
   *unchanged* `SamplerState Samplers[2]` parameter compiles with no error.

Claim 3 is the load-bearing one for triage: it is what makes this a **bug** rather than an
unsupported construct. If two source files that differ only by an unrelated, unreferenced
struct declaration compile differently, the diagnostic is spurious.

## What "this reproduces" means

### Symptom A — primary (`match.json`)

Compiling a shader that declares a function with a `SamplerState Samplers[2]` parameter, with
**no** preceding struct containing a sampler array, emits the exact diagnostic

```
error: variable has incomplete type 'SamplerState [2]'
```

and fails the compile. Matching "any error" is explicitly *not* enough: a release that
predates sampler arrays entirely would also error, and would be scored as a reproduction. The
predicate must quote this diagnostic and must also require the compile to have failed on the
parameter, not on something incidental.

### Symptom B — secondary, SPIR-V (`match-spirv-struct.json`)

Compiling the struct workaround with `-spirv` fails validation with
`OpTypeStruct must not contain an opaque type` (VUID-StandaloneSpirv-None-04667).

Symptom B has its own history and must not be folded into A: A "fixed" while B still fails is
a real and reportable outcome, and a single conjunction would hide it.

## The hazard specific to this issue, and the defence

**The reported symptom is itself a diagnostic.** The `invalid-probe` machinery only protects
against a release that *could not run* the repro; it does nothing when the symptom *is* an
error message. A release that never supported sampler arrays as function parameters at all
would emit its own error — possibly the very same `incomplete type` wording, since that
diagnostic is generic Clang — and score as a textbook reproduction. `classify`'s
feature-absence marker list does not contain `variable has incomplete type`, so nothing in the
tooling will flag it.

**Defence, decided up front, before any measurement:** every probed release gets a
**positive control that proves the construct is supported there**, and a release that fails
the control is disqualified rather than counted.

The control is claim 3 itself: the identical function, preceded by
`struct Resources { SamplerState Samplers[2]; };`. It differs from the repro in exactly one
way — an unreferenced struct declaration.

- control **clean** + repro **matches** → that release genuinely exhibits the reported defect.
- control **fails too** → that release does not support sampler-array parameters in either
  form. Its failure is *not* the reported defect and it is not valid evidence, regardless of
  what the diagnostic says.

Two supporting controls, also per release:

- `control-global-sampler-array.hlsl` — a plain global `SamplerState S[2]`, indexed, proving
  the release understands sampler arrays at all.
- `control-texture-array-param.hlsl` — `Texture2D<float4> Textures[4]` as a parameter with the
  sampler dropped, proving that resource-array *parameters* work and isolating the failure to
  `SamplerState`.

And one negative control for the predicate itself: a shader with no sampler array whatsoever
must score `no-match`, or the predicate is matching something other than this bug.

## Predicted outcomes (recorded so they can be wrong)

- Ground truth `main-debug` reproduces symptom A. The issue was acknowledged as a live bug by
  a maintainer in Aug 2024 and marked dormant, i.e. not fixed.
- History is the open question. "Used to work just fine" asserts a regression, so a `--linear`
  scan is required — a binary search over agreeing endpoints would report `always-repro'd` and
  silently erase a working window. The reporter's claim is a claim, not a measurement, and the
  controls are what decide whether an old clean release is a genuine "it worked" or an
  artefact.

## Repro quality

`complete` for the minimal form. The issue body is prose-plus-fragments from a 175-line
private shader, but a collaborator (`llvm-beanz`, a DXC maintainer) published a one-line
reproduction in the thread, and the body's three claims are each directly expressible. Nothing
here is agent-invented; the repro line is copied from the linked Compiler Explorer session.

## Out of scope

The reporter's original 175-line `hlsl.hlsl` is not attached, so "used to work just fine" can
only be tested against the minimal form. If the minimal form and the real shader diverge, this
triage measures the minimal form and says so.
