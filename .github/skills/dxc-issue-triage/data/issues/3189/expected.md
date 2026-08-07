# #3189 — [SPIR-V] Descriptor bindings assigned before dead code elimination

*Written before any compiler was run.* Derived from the issue body (2020-10-07) and its three
comments (2021-09-02, 2024-07-03 x2), read in full.

## What the reporter claims

A pixel shader declares, in this order:

1. `Texture2D g_texture2D;` — used
2. `sampler g_sampler;` — used
3. `cbuffer a { float4x4 g_a; };` — **unused**
4. `cbuffer b { float4x4 g_b; };` — **unused**
5. `cbuffer c { float4x4 g_localToClip; float4 g_randomOffset; float4 g_colorAdd; };` — used
   (`g_colorAdd` is read by `mainPS`)

No resource carries a `:register()` annotation or a `[[vk::binding()]]` attribute.

The reporter adds, parenthetically: *"I am using the shift functionality to move the textures
and samplers so that buffer start at 0"* — i.e. `-fvk-t-shift`/`-fvk-s-shift` are in play, which
per `docs/SPIR-V.rst` require `-fvk-auto-shift-bindings` to apply to resources with no
`:register()`. The exact command line is **not given in the issue**; reconstructing it is part
of step 3 and any departure must be recorded.

**Reported:** `c` is decorated `Set 0, Binding 2`.
**Reporter's expectation:** `Set 0, Binding 0`, because the SPIR-V module visibly no longer
contains `a` and `b` — they were dead-code-eliminated — so in the reporter's view they should
not have consumed binding numbers 0 and 1.

The reporter also confirms the elimination happened: *"In the resulting Spirv I can see that
the two unused Cbuffers have been eliminated but the binding index doesn't reflect that."*

## What "this reproduces" means

**The symptom is a specific decoration value**, so the predicate can be positive and exact:

> The `OpVariable` created for cbuffer `c` carries `OpDecorate ... Binding 2` (and
> `DescriptorSet 0`), while no variable for `a` or `b` survives in the module.

That is: the compile **succeeds**, emits valid SPIR-V, and the surviving used cbuffer sits at a
binding number that counts the eliminated ones. A clean exit code is expected and is *not*
evidence that the symptom is absent — this is a wrong-output issue, not a failure issue.

It does **not** reproduce if `c` lands at `Binding 0` under the reporter's configuration, i.e.
if binding numbers today are compacted to the resources that survive optimisation.

### Control required

The predicate must be given a negative control: **the same shader with `a` and `b` deleted**,
under the identical command line. There the used cbuffer is legitimately the first `b`-type
resource and must land at `Binding 0`, so the predicate must **not** fire. If it fires on that,
the predicate is matching something other than "the dead cbuffers consumed bindings".

## What is *not* being decided here

The reporter asks "Is it possible to get this kind of behaviour?" — a question, not a defect
report. Two later comments bear directly on whether the current behaviour is wrong at all:

- **damyanp (member, 2024-07-03)** observes this differs from how DXIL mode allocates bindings,
  linking https://godbolt.org/z/KMqqb5faE.
- **s-perron (collaborator, 2024-07-03)** states a design position: SPIR-V binding numbers are
  deliberately not expected to match DXIL; changing the default *"could break many people who
  rely on the current behaviour"*, specifically users who rely on an unused resource still
  consuming a binding so that VS and PS binding layouts match; and the suggested route is an
  opt-in `spirv-opt` renumbering pass exposed as a DXC option, which the SPIR-V maintainers do
  not have the resources to write.

So triage must establish **what DXC does today and whether that is documented/deliberate**, and
must not assert that binding-after-DCE is the correct behaviour. A host application binds by
number; renumbering resources according to whether the compiler happened to eliminate one is a
real hazard, not obviously an improvement. Whether to add an option is a product decision and
is explicitly out of scope for this triage.

## Repro quality

`complete` — the issue supplies a self-contained shader that compiles as-is. The only thing
missing is the exact shift flags, which are described in prose; both the as-filed
(shift-flag) configuration and a plain `-spirv` configuration should be measured, and the
difference recorded rather than assumed.

## Bisection hazard, recorded up front

**v1.4.1907 ships no SPIR-V codegen** — it answers `SPIR-V CodeGen not available` — so it
cannot answer this question and must classify as `invalid-probe`, not as a clean run. SKILL.md
records that this exact case has faked a regression before. The classification must be
*confirmed from the capture header*, not assumed.
