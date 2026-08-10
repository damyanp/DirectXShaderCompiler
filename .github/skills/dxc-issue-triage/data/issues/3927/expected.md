# #3927 — expected symptom (written before running the compiler)

**[SPIR-V] Not all unnecessary bindings are eliminated using SPIR-V backend**
Filed 2021-09-02 by `stil-t`, tested by the reporter on `dxc_2021_07_01`. Label: `spirv`.

## What the report says

A pixel shader declares two texture/sampler pairs. `Tex0`/`SS0` are sampled, the result feeds
an `if` condition, and **both** arms of the resulting control flow end in `clip()`:

```hlsl
const float2 val = Tex0.Sample(SS0, In.texCoord).xy;
if (((val.x == 0.0f) && (val.y == 0.0f)))
{
    clip(-1.0f);          // -> OpKill
}
clip(-0.5f);              // -> OpKill, unconditional
return Tex1.Sample(SS1, In.texCoord);   // unreachable
```

Compiled with `dxc -T ps_6_0 -spirv test.hlsl -Fo test.spv` (no `-O` flag, no `-fcgl`, no
`-Vd`, so **default optimisation** — the reporter filed no workaround flags) and inspected
with `spirv-dis`, the reporter observes:

- `Tex1` and `SS1` **are** eliminated — they are only used on the unreachable `return`;
- `Tex0` and `SS0` **are not** — the module still carries
  `OpDecorate %Tex0 Binding 0` / `OpDecorate %SS0 Binding 1` and the `OpImageSampleImplicitLod`
  that feeds the branch, even though every path through `main` ends in `OpKill`, so the sample
  result cannot affect any output.

The reporter's argument: the whole function could collapse to a single `OpKill` and then both
bindings would go too. Hence "not *all* unnecessary bindings are eliminated".

`s-perron` (COLLABORATOR, 2024-08-22) states the fix location: spirv-opt would need a pass
that recognises the two targets of a branch are semantically the same and folds the branch.
"This is not currently in our plans, but we would accept a fix if someone else were to
implement it." So as of 2024-08 a maintainer regarded this as unfixed and unplanned.

## What "this reproduces" means

Ground truth reproduces the issue when, for the reporter's shader compiled with the
reporter's flags, **the emitted SPIR-V module still binds `Tex0` and `SS0`**:

- a valid module is produced (`OpEntryPoint Fragment %main` is present — this is the positive
  anchor; without it a failed compile that emits nothing would satisfy any "binding survives"
  test vacuously, and a "binding is gone" test even more so), **and**
- `OpDecorate %Tex0 Binding …` is present, **and**
- `OpDecorate %SS0 Binding …` is present.

## What each other verdict would look like

| observation | verdict |
| --- | --- |
| module compiles, `%Tex0`/`%SS0` bindings gone (ideally only `OpKill` left) | `does-not-repro` — the optimiser learned to fold the kill-only branch |
| module compiles, `%Tex0`/`%SS0` bindings still present | `repros` |
| `Tex1`/`SS1` bindings now survive too, or the shader errors out | `changed-behavior` — regression relative to the report |
| `-spirv` rejected (`SPIR-V CodeGen not available`, `0x80070057`) | **invalid probe**, not a clean result. Releases before SPIR-V codegen existed cannot answer this question at all, and scoring them as "no symptom" would fake a regression at the first SPIR-V-capable release |

## Repro quality

**`complete`** — the issue body contains the full shader and the exact command line, and the
expected/observed disassembly is quoted in full. Nothing has to be reconstructed.

## Things to be careful about (recorded before measuring)

1. Every command needs `-spirv`; without it this measures the DXIL path and means nothing.
2. Optimisation level is load-bearing. At `-O0` no spirv-opt runs, so *nothing* would be
   eliminated and even `Tex1`/`SS1` would survive — that is not the reported symptom. The
   reporter used the default, so the default is the primary configuration.
3. `-Fo test.spv` writes a binary the predicate cannot read. Dropping `-Fo` makes dxc print
   the SPIR-V assembly to stdout, which is exactly what the reporter read via `spirv-dis`;
   codegen is unchanged. This is the only deviation from the filed command line.
4. The predicate must not be satisfiable by a compile that failed, and must not match a
   shader whose bindings *were* correctly eliminated. Both need controls.
