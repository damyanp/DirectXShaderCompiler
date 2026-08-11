# Issue 4666 — triage notes

**Verdict: reproduces on `main`. Symptom A is a regression whose boundary is
`v1.7.2207`.** The construct was accepted by every release before that and is
rejected by every release since.

Ground truth: `main-debug`, `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433)`, recorded build
commit `13730886e6a9019e4e0823746470f3ab75341d6b`. Compiler Explorer corroboration:
https://godbolt.org/z/1Mbe8oPcj

The binary's own banner names `ab540090` while the compilers table records `13730886` for the
same build; the comment quotes the banner, which is the binary's own statement about itself.

---

## What the issue reports

Three claims, all testable, all separately measured:

| | Claim | Result |
|---|---|---|
| A | `SamplerState Samplers[2]` as a function parameter is rejected with `variable has incomplete type` | **Reproduces.** Regressed in v1.7.2207 |
| B | Putting the sampler array in a struct works for DXIL, but SPIR-V then rejects the module | **Reproduces**, with a large caveat about *when* |
| C | Merely declaring the struct *before* the function makes the error disappear | **Confirmed**, and it turns out to be the key to the whole thing |

---

## Symptom A — the reported diagnostic

`repro.hlsl` is the one-line form published in the thread by llvm-beanz
(https://godbolt.org/z/39Khq117f), plus an entry point so it compiles under a
non-library profile. The profile makes no difference: `ps_6_0`, `lib_6_3` and
`lib_6_6` all produce a byte-identical diagnostic (`variant-libprofile-*`), so
`cmd.txt` uses `ps_6_0`, which reaches furthest back through the release
history. `cmd-as-filed.txt` keeps the collaborator's original `lib_6_6` line.

```
repro.hlsl:12:61: error: variable has incomplete type 'SamplerState [2]'
void Reflection(Texture2D<float4> Textures[4], SamplerState Samplers[2]) {}
                                                            ^
```

exit `0x80004005` (E_FAIL — an ordinary diagnosed error, not a crash).

### History

`bisect --linear` over the stable releases, then re-measured independently by
`measure-history.py`:

| | |
|---|---|
| clean | v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106, v1.6.2112 |
| reproduces | **v1.7.2207** … v1.9.2607 (15 stable releases) and `main-debug` |

Five prereleases were skipped by policy (v1.5.2003, v1.8.2306-preview,
v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24) and v1.2.0-alpha has
no `dxc` asset. The issue names no prerelease, so no `release-policy.json`
opt-in was warranted.

The reporter's build, commit `42eb79311` (2022-09-16), is after v1.7.2207
(2022-07-13), consistent with them seeing it and not seeing it earlier.

### The trap this issue sets, and the control that defuses it

The reported symptom **is a diagnostic**. The tooling's `invalid-probe` guard
protects against a release that could not run the repro; it does nothing when
the symptom is itself an error message, because a release predating the feature
emits its own error and scores as a textbook reproduction.
`classify()`'s feature-absence marker list does not contain `variable has
incomplete type`, so nothing would have flagged it.

So every probed release also ran `control-struct-first.hlsl` — byte-identical to
`repro.hlsl` apart from an unreferenced `struct Resources { SamplerState
Samplers[2]; };` ahead of the function, i.e. claim C. If sampler arrays were
simply unsupported on some release, the control would fail there too and that
release would be disqualified rather than counted.

**`ctl-struct-first` scored `ok` on all 21 targets, including all 16 that
reproduce.** Sampler-array parameters are supported everywhere probed. The
diagnostic is spurious, not a missing feature. This is the single strongest
piece of evidence in the whole triage.

`match.json` matches the *exact* diagnostic text, not "any error", for the same
reason.

---

## Root cause characterisation (`manual-case-completion-probe.txt`)

The repro pairs a texture array and a sampler array; only the sampler is
diagnosed. That asymmetry turned out to be the whole story. Ten minimal
single-parameter shaders on `main-debug`:

| case | shader | result |
|---|---|---|
| A | `void R(Texture2D<float4> T[4])` | ok |
| I | `void R(RWTexture2D<float4> T[2])` | ok |
| B | `void R(SamplerState S[2])` | **diagnosed** |
| H | `void R(SamplerComparisonState S[2])` | **diagnosed** |
| J | `void R(ByteAddressBuffer B[2])` | **diagnosed** |
| C | `void R(SamplerState S)` — scalar | ok |
| D | global `SamplerState g;` **before** | ok |
| E | the same global **after** | **diagnosed** |
| F | struct with the member **before** | ok |
| G | `typedef SamplerState T2[2];` before | **diagnosed** |

Read together:

* It is not about samplers. **Templated** builtin object types are fine;
  **non-templated** ones (`SamplerState`, `SamplerComparisonState`,
  `ByteAddressBuffer`) are rejected. `Texture2D<float4>` in the reported repro
  is a red herring.
* Only the array form is affected — the same type as a scalar parameter is
  accepted (C).
* It is order-dependent: anything earlier in the file that requires the type to
  be *complete* suppresses it (D, F); the same declaration later does not (E);
  merely naming the type does not (G). That is exactly what makes claim C true.

All three of B, H and J were accepted by v1.6.2112, so the whole family
regressed together.

### Where it probably comes from — hypothesis, not measurement

Two commits in the v1.6.2112 → v1.7.2207 window are directly on this path:

* `77945a157` "Make external sema source handle type completion" (#4317,
  2022-03-07) changed builtin object types from being created complete to being
  created **incomplete and completed on demand** by
  `HLSLExternalSource::CompleteType` (`tools/clang/lib/Sema/SemaHLSL.cpp:6262`).
  That is the change that makes "incomplete" reachable at all.
* `dbd8db0e8` "Complete builtin types when used as array params" (#4379,
  2022-04-08) added the HLSL block in `Sema::RequireCompleteTypeImpl`
  (`tools/clang/lib/Sema/SemaType.cpp`, ~line 6734) that strips the array and
  asks the external source to complete the element type.

The regression test added with #4379,
`tools/clang/test/HLSLFileCheck/hlsl/template/complete-array-parameter.hlsl`,
covers `Texture2D f[2]` — a **templated** element type — only. That is precisely
the case that works. There is no test anywhere in `tools/clang/test` for the
non-templated form; a search for the diagnostic text returns nothing.

I did not build intermediate commits, so this is correlation plus a visible
coverage gap, not a bisect. Release granularity is as far as I measured.

---

## Symptom B — invalid SPIR-V from the struct workaround

`repro-spirv-struct.hlsl`, `-T ps_6_0 -E main -spirv`:

```
fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-None-04667] In Vulkan, OpTypeStruct must not contain an invalid opaque type.
  %Test = OpTypeStruct %_arr_type_sampler_uint_2
```

The operand matches the issue body character for character.

**`[noinline]` is required and is a deviation from anything the reporter wrote.**
My first reconstruction used a plain helper and compiled clean on main,
v1.6.2112, v1.7.2207 and v1.7.2212 — DXC inlines the helper, so the struct type
is never materialised and no `OpTypeStruct` is ever emitted. `-Od`, `-fcgl`, a
global struct instance and a raytracing `lib_6_3` entry all failed to reproduce
it too. Only `[noinline]` exposes it. The reporter's real shader is a ray-tracing
helper, which plausibly is not inlined; the identical operand is the reason I
believe the reconstruction is faithful. `control-spirv-struct-inlined.hlsl` is
the same shader without `[noinline]` and is clean, which isolates the trigger.

### The apparent v1.6.2106 boundary is not a DXC change

Naively, symptom B looks clean before v1.6.2106 and broken after. It is not:

* **v1.4.1907** — `SPIR-V CodeGen not available`. No evidence either way.
* **v1.5.2010** — does not honour `[noinline]`; emits no `OpTypeStruct` at all.
  Recorded as `CONTROL-NOT-MATERIALISED`, i.e. unmeasurable — *not* clean.
* **v1.6.2104** — emits `%Test = OpTypeStruct %_arr_type_sampler_uint_2` and
  **exits 0**, because its bundled SPIRV-Tools predates
  `VUID-StandaloneSpirv-None-04667`. The malformed module is present and simply
  undiagnosed.

So the boundary is a **SPIRV-Tools validator upgrade**, not a DXC regression.
DXC has emitted this module for as long as it can be measured. That is why the
matrix carries `-Vd` arms and `match-spirv-badir.json`: the structural question
"is the bad type emitted" is separable from "does the validator complain".

The validator's wording also drifts — "must not contain an **opaque type**"
through v1.8.2505.1, "must not contain an **invalid** opaque type" from
v1.9.2602. `match-spirv-struct.json` uses `(?:invalid )?`; a naive predicate
would have invented a fix at v1.9.2602.

Symptom B is therefore `always-repro'd` as far as it can be measured, and is a
separate defect from symptom A. It is not what drives the `history` field, which
records the primary reported symptom.

---

## Adjacent finding — the DXIL workaround crashes when not inlined

Not the reported symptom; found while building the controls, and worth a
separate issue.

`observation-noinline-struct-sampler-array.hlsl` — the issue's own struct
workaround with inlining suppressed, compiled to **DXIL** — does not produce a
diagnostic. It crashes:

* `main-debug` → `0xE0000001`, `Internal compiler error: LLVM Assert`
* v1.6.2112, v1.7.2207, v1.9.2607 → `0xC0000005`,
  `Internal compiler error: access violation. Attempted to read from address 0x0`

It reproduces on **v1.6.2112**, which does not have symptom A, so it is an older
and independent defect. The array is load-bearing:
`observation-noinline-struct-sampler-scalar.hlsl`, the same shader with a scalar
`SamplerState` member, gives an ordinary
`phi/select disallowed on pointers to local resources` diagnostic instead.

This matters for the issue because the workaround the reporter recommends is
only safe while the callee is inlined.

---

## What I got wrong mid-flight

1. **The first SPIR-V reconstruction was silently unfaithful.** It compiled
   clean everywhere and I nearly recorded symptom B as fixed. It was not
   reproducing the symptom at all — the helper was being inlined away. Corrected
   with `[noinline]`; the unfaithful file was deleted.
2. **I predicted the DXIL struct workaround would be clean and it crashed.** The
   probe was run with `--expect no-match` under the primary symptom's predicate;
   it returned an internal compiler error. That falsified prediction is how the
   adjacent crash below was found. The capture has since been re-filed under
   `match-noinline-struct-ice.json` with `--expect match`, which is what it
   actually is — a crash probe, not a control for symptom A.
3. **An early version of the matrix scored v1.5.2010 and v1.6.2104 "clean" for
   symptom B.** Both were instrument artefacts — one an un-materialised control,
   one a validator that did not yet have the rule. Fixed by adding `-Vd` arms and
   a materialisation self-test, and the matrix was re-run.

## What I could not measure

* **The reporter's original `hlsl.hlsl`** (the error cites line 175) is not
  available, so "used to work just fine" is only testable against the minimal
  form. The v1.6.2112 → v1.7.2207 transition corroborates it and matches the
  September 2022 filing date.
* **The exact regressing commit.** Release granularity only; the two candidates
  above are a hypothesis.
* **Symptom B on v1.4.1907 and v1.5.2010** — no SPIR-V backend, and `[noinline]`
  not honoured, respectively.
