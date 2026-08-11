# Issue 4619 — expected symptom

**Title:** How to get thread group size and output primitive topology in MeshShader?
**Filed:** 2022-08-26 by `syddf`. **Comments: 0.** Labels: `enhancement`, `reflection`.
Milestoned to `Backlog` (2024-09-30).

Written **before** running anything.

## What the issue says

Verbatim body, in full:

> I tried ID3D12ShaderReflection::GetThreadGroupSize, but got 0, 0, 0 all the time
> And I can't find the primitive topology output for mesh shader

## Shape of the issue

This is a **question about the reflection API surface**, not a defect report about
code generation. It is phrased as "how do I get X", and the maintainers agreed with that
reading: `llvm-beanz` removed `needs-triage` and applied `enhancement` + `reflection` on
2024-01-18. Nobody has ever replied to the reporter.

So there are two separable asks, and they must be scored separately (SKILL.md: "Decompose
multi-ask issues before choosing one verdict"):

### Ask A — thread group size via `ID3D12ShaderReflection::GetThreadGroupSize`

"This reproduces" means: for a mesh shader (`ms_6_5`) declaring `[numthreads(X,Y,Z)]` with
at least one of X/Y/Z != 1, `ID3D12ShaderReflection::GetThreadGroupSize(&x,&y,&z)` writes
**0, 0, 0** and returns 0, rather than X, Y, Z.

"This does not reproduce" means it returns the declared numthreads.

Anti-vacuity requirements — without these the measurement is worthless:

* the same harness, run against a **compute** shader with the same `[numthreads]`, must
  return the declared values. That is the positive control proving the harness, the
  container and the accessor all work. If the compute case also returns 0,0,0 then the
  instrument is broken and the mesh result means nothing (SKILL.md: "a control cannot catch
  a broken reader" / "make the instrument prove it can detect a presence in the same run").
* the thread group size must demonstrably be **present in the container**, otherwise the
  finding is "dxc does not record it", which is a different (and bigger) bug than "the
  reflection accessor does not surface it". Check the DXIL `!dx.entryPoints` numthreads
  metadata and/or the PSV0 part for the same shader.

### Ask B — output primitive topology for a mesh shader

"This reproduces" means: no member of the `ID3D12ShaderReflection` surface returns the mesh
shader's output topology (`line` / `triangle`, from the `outputtopology` attribute), so a
caller genuinely cannot get it.

The relevant candidate accessors are `GetDesc` → `D3D12_SHADER_DESC` (which carries
`GSOutputTopology` and `InputPrimitive`, both documented for geometry shaders), plus the
tessellation-specific fields. If `GSOutputTopology` is populated for a mesh shader, ask B
does **not** reproduce and the answer to the reporter is simply "use this field".

Anti-vacuity requirement: a **geometry** shader run through the same harness must populate
`GSOutputTopology`, proving the field is read and printed at all.

## Predicted classification, stated now so it cannot be rationalised later

The honest outcomes available here are:

* `repros` + `enhancement-not-bug` — the information is not retrievable through the
  reflection API today, and the fix is to add/expose it. This is what the maintainer labels
  already assert, but nobody has ever measured it.
* `does-not-repro` — there is in fact an accessor that returns it, in which case the useful
  output is the **answer to the question**, four years late.
* `not-compiler-verifiable` — only if no instrument can reach `ID3D12ShaderReflection`.
  (I expect this to be false: `dxa -dumpreflection` and a direct `IDxcContainerReflection`
  host program both drive the real interface.)

`inconclusive` if the two asks disagree in a way I cannot separate.

**A forced bug-shaped verdict is not on the list.** The reporter asked a question. If the
answer is "the compiler does not expose it", that is an enhancement, not a regression, and
the history question ("when did it break") may have no meaningful answer.

## Repro quality

**`prose-only` as filed** — the issue contains no shader, no API code, no build version, and
no attachment. Any repro is mine. Recording as `agent-constructed`.

## What would make this unmeasurable

* If `dxa`/`D3DReflectionDumper` never call the accessor under test, an empty dump proves
  nothing (SKILL.md: "an absent field proves nothing if it never calls the accessor"). Read
  the dumper source before believing a blank.
* Release-history probing needs the reflection *reader* held fixed while each release's
  `dxcompiler.dll` produces (and reflects) the container. `triage.py bisect` drives each
  release's `dxc.exe`, which never calls a reflection interface — so bisect would score every
  release `no-repro` and confidently report the inverse. **Do not run `bisect` here.** Use a
  fixed-harness release matrix, as issue 3237 did.
