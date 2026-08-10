# #3362 — pack-optimized issue with domain shader

**Verdict: does not reproduce.** With `-pack-optimized` used as documented — passed to *every*
stage, with an identical interstage signature — the domain-shader output signature and the
pixel-shader input signature agree exactly, on `main` and on every release back to v1.4.1907
(July 2019, 18 months before this issue was filed). The mismatch in the report is fully
explained by the reporter's own attached command lines: the pixel shader was compiled **without**
the flag.

Triaged against `main` @ `13730886e` (local Debug build; it self-reports a fork-local commit
string, so `13730886e` is the upstream commit whose compiler source is identical).

## What the report contains

Three signature tables and a D3D12 PSO-creation error
(`CREATEGRAPHICSPIPELINESTATE_SHADER_LINKAGE_REGISTERMASK`), plus `disasm.zip` with the full
disassemblies. The HLSL sources are not included, so the repro here is reconstructed
(`agent-constructed`) around a real and well-evidenced report.

The struct, shared between stages via a header:

```hlsl
struct PixelInput {
    float4 pos  : SV_POSITION;
    float  clip : SV_ClipDistance0;
    float4 pre  : PREVIOUSPOSITION;
    float3 nor  : NORMAL;
};
```

**The attachment is the decisive artifact.** Each dumped disassembly begins with the command
line that produced it (recovered into `cmd-as-filed.txt`). The domain-shader dumps carry
`-pack-optimized`; the pixel-shader dump does not.

## What was tested

`repro.hlsl` declares `PixelInput` once and defines both `DSMain` (`[domain("tri")]`,
`OutputPatch<PixelInput,3>`, plus a patch-constant input) and `PSMain`. Two controls:

* `control-pipeline.hlsl` — a whole VS→HS→DS→PS pipeline sharing both the interstage struct
  *and* a patch-constant struct with user semantics (`MIDPOINT`, `CLIPPLANE`). **Negative
  control**: the predicate must *not* match.
* `control-subset-ps.hlsl` — DS emits the 4-element struct, PS declares only 3 of them (no
  `NORMAL`), which is the reporter's actual situation. **Positive control**: the predicate must
  match, proving it can fire at all.

`run-matrix.py` drives an 11-configuration matrix (stage × flag × shader) and echoes every
command; output is `manual-case-configurations.txt` (`main-debug`) and
`manual-case-v1.4.1907-underscore.txt` (oldest release).

## Results

`SV_ClipDistance` register/mask, identical on `main-debug` and on v1.4.1907:

| configuration | flag | `SV_ClipDistance` |
| --- | --- | --- |
| `repro.hlsl` DS output | `-pack-optimized` | `w` @ r2 |
| `repro.hlsl` PS input | `-pack-optimized` | `w` @ r2 — **agrees** |
| `repro.hlsl` PS input | *(default)* | `x` @ r1 — **the table in the issue** |
| `control-subset-ps.hlsl` PS input | `-pack-optimized` | `x` @ r2 — still disagrees |
| `control-pipeline.hlsl` VS/HS/DS/PS | `-pack-optimized` | `w` @ r2 at every stage |

All four rows agree, not just the clip row: with the flag on both stages the DS output table
and the PS input table are byte-identical (`PREVIOUSPOSITION` r0 `xyzw`, `SV_Position` r1
`xyzw`, `SV_ClipDistance` r2 `w`, `NORMAL` r2 `xyz`).

The full pipeline agrees on the **patch-constant** signature too — HS `PCOut` and DS
patch-constant both give `CLIPPLANE` r0 / `SV_TessFactor` 0,1,2 at r1.w, r2.w, r3.w /
`MIDPOINT` r1.xyz / `SV_InsideTessFactor` r4.x. The domain shader's second signature, the
obvious suspect for a stage-specific packing bug, is handled consistently.

## Why the reporter's PS table cannot have come from optimized packing

Two independent lines of evidence:

1. Their own recorded command line for the pixel shader (`attach/pixel_pack_optimized`, line 1)
   has no `-pack-optimized`.
2. `PackOptimized` (`include/dxc/HLSL/DxilSignatureAllocator.inl:311`) allocates 4-component
   elements first, so an arbitrary `float4` (`PREVIOUSPOSITION`) is placed *before*
   `SV_Position`. It can never put `SV_Position` at register 0 for this element set — but the
   reporter's PS table does. Compiling their 3-element subset PS with **default** packing
   reproduces their table exactly, Mask/Register/SysValue columns included.

So two preconditions were violated, and either alone is enough to produce the reported PSO
error:

* the flag was not passed to every stage; and
* the pixel shader's signature is a strict *subset* of the domain shader's (no `NORMAL`).
  Optimized packing is a global optimisation over the whole element list, so dropping one
  element reshuffles the rest: DS gives clip `w` @ r2, subset-PS gives `x` @ r2. Even with the
  flag on both stages, that configuration mismatches.

This is what the flag's help text means by *"Optimize signature packing assuming identical
signature provided for each connecting stage"* (`include/dxc/Support/HLSLOptions.td:301`).

## History

`bisect --linear`: **never reproduced** across v1.5.2010 … v1.9.2607, with one release
demoted `invalid-probe`. The positive control was then run on all 19 probed releases and
matched on every one, so the predicate could have fired throughout — the `no-repro` result is
a real measurement, not a dead predicate.

**v1.4.1907 was demoted for a spelling reason, not a missing feature.** It rejects
`-pack-optimized` (`Unknown argument`) but accepts `-pack_optimized` and `/pack-optimized`.
Re-probed with the underscore spelling it compiles all 11 configurations and produces layouts
identical to `main`. The flag has existed since at least July 2019 — there is no regression
here, and none should be reported. (The in-tree tests still use the underscore spelling.)

## Not the reported symptom, recorded for completeness

The DS **patch-constant** table's `Used` column looks self-inconsistent on `main-debug`:
`SV_TessFactor` shows `xyzw` against a `w`-only Mask, `MIDPOINT` shows `w` against an `xyz`
Mask, and `CLIPPLANE` is blank although the DS reads it. It is identical with and without
`-pack-optimized`, and v1.4.1907 prints `xyzw` on every row instead. Out of scope for this
issue and not diagnosed here; noted only so a later reader is not surprised by it.

## Documentation and test coverage (the actionable residue)

* `-pack-optimized`'s only prose documentation is `docs/SPIR-V.rst:1744`, which describes the
  SPIR-V Component-decoration behaviour. For DXIL the contract exists solely as the one-line
  `--help` string. Nothing states that the flag must be applied to every stage in the PSO, or
  that a subset signature will not survive it.
* The three DXIL regression tests
  (`tools/clang/test/HLSLFileCheck/hlsl/compile_options/pack_optimized/optimized{,2,3}.hlsl`)
  are all `vs_6_0`, single stage. No hull/domain coverage, no patch-constant coverage, and no
  test that two connected stages agree.

Given the maintainer's 2024 comment inviting PRs, either would be a small, well-scoped
contribution.

## Suggested action

`enhancement-not-bug`. Not `close-fixed` — nothing was fixed, and saying so would be false.
The compiler does what the flag documents, so the defect claim does not survive the evidence;
what remains is a request rather than a bug: `-pack-optimized` silently produces a layout the
connecting stage cannot match, and the failure only surfaces at `CreateGraphicsPipelineState`.
Whether DXC should diagnose that, or tolerate a subset signature, is a design decision — but
the documentation and test gaps above are unambiguous and small enough to be worth doing
either way, which is a good fit for the maintainer's 2024 invitation to submit PRs.

`text_stale` is set narrowly. The runtime linkage error may be exactly what was observed, and
the compiler's packing behaviour has not drifted. But the body says the quoted pixel-shader
table was produced "when using `pack-optimized`", while the attached dump's embedded command
line omits the option and the table matches default packing. That configuration description
no longer supports the comparison the text asks a reader to make.
