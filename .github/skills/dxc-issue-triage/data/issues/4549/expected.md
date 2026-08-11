# #4549 — expected symptom

**Written before running any compiler.**

Issue: "[HLSL] Misleading error message when using a UAV register for a raytracing
acceleration structure", filed 2022-07-12 by DethRaid. One comment (damyanp, 2024-04-23)
asking tex3d for initial investigation. Label: `diagnostic`. No cross-references on the
timeline.

## What the reporter did

```hlsl
RaytracingAccelerationStructure opaque_as : register(u0);

Texture2D<float> depth_buffer : register(t0);
```

`RaytracingAccelerationStructure` is an SRV-class resource in HLSL, so `register(u0)` is
wrong. The reporter's objection is not that the shader is rejected — it is *how* it is
rejected.

## What the reporter observed

> `... error GDA5BD758: resource depth_buffer at register 0 overlaps with resource opaque_as
> at register 0, space 0`

(The `GDA5BD758` token is not DXC's; it is almost certainly the reporter's engine wrapping
DXC's message. The DXC-side substance is the `resource ... overlaps with resource ...`
diagnostic.)

## What the reporter expected

> "raytracing acceleration structures must use SRV registers instead of UAV registers"

## Substance of the complaint (this is what the predicate must test)

Three separable claims, only some of which are about wording:

1. **The `u` register class on the acceleration structure is ignored.** The AS is bound as
   if it had been written `register(t0)`. (Brian Favela's speculation, quoted in the body.)
2. **Consequently the compiler reports a *collision with an innocent resource*.** The
   diagnostic names `depth_buffer`, which is correctly declared and is not the mistake.
3. **No diagnostic anywhere in the output says the acceleration structure needs an SRV /
   `t` register**, which is the fact that would let the developer fix it.

Claims 1–3 are behavioural, not cosmetic. A pure rewording of the overlap message (e.g.
"binding overlap at t0 between depth_buffer and opaque_as") would leave all three true and
**must not** be scored as a fix. Conversely, the issue is answered if DXC either diagnoses
the register-class mismatch on `opaque_as` directly, or at minimum stops blaming
`depth_buffer`.

## "This still reproduces" means

Compiling the two declarations above (with a trivial entry point that uses both, so neither
is dead-stripped):

- the compile **fails**, and
- **an error names `depth_buffer`** — i.e. the innocent, correctly-declared resource is
  implicated, and
- **no diagnostic connects the acceleration structure to an SRV / `t` register
  requirement** — no mention of `RaytracingAccelerationStructure`/"acceleration structure"
  together with SRV or `t` register, and no register-type-mismatch diagnostic of the
  "expected 't' but found 'u'" family naming `opaque_as`.

## "This does not reproduce" would mean

Any of:

- DXC emits a diagnostic naming the register-class mismatch on `opaque_as` (whatever its
  wording), or
- the diagnostic no longer implicates `depth_buffer`, or
- the shader compiles clean (which would be a *different*, worse bug — silently binding an
  AS to a UAV slot — and would be reported as `changed-behavior`).

## Anticipated confounders

- **Wording is the least portable thing DXC emits.** Release-to-release rewording and the
  Windows/Linux split both change message text. Predicate must be keyed to *which resource
  is blamed* and *whether the AS/SRV requirement is stated*, not to a sentence.
- **This is a diagnostic-quality issue**, so the `invalid-probe` classifier's
  feature-absence markers can collide with the symptom itself (SKILL.md §6). Watch the
  `# invalid-probe-reason:` headers.
- **`RaytracingAccelerationStructure` is a DXR 1.0 type** (SM 6.3+). Old releases may
  reject it as an undeclared identifier or reject the profile, which is an `invalid-probe`,
  not a clean run. Needs a feature-presence control per release.
- **An absence clause is satisfied for free by a failed parse.** Clause 3 above is an
  absence; it must be anchored by clause 2 (a positive fact that requires the compiler to
  have got as far as binding resources).
- The reported message may come from DXIL validation rather than Sema. Attribute it from
  the emitting source, not from its formatting (SKILL.md §3).

## Repro quality

**complete** — the issue body gives the two declarations verbatim and the exact observed
message. The only thing an agent must add is an entry point, because two globals alone are
not a shader. That addition is recorded in `notes.md`.
