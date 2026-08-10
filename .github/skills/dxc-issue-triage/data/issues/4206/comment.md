> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#4206](https://github.com/microsoft/DirectXShaderCompiler/issues/4206).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and the reflection dump is wrong in
**two** ways for this shader, not one.

Compiling the shader from the report as `-T cs_6_0 -E ResampleCS` and reading the container's
reflection back with `dxa -dumpreflection`:

| `$Globals` variable | offset | read by the shader? | reported `uFlags` | |
| --- | --- | --- | --- | --- |
| `WorldPosToProbeCoord[6]` | 0 | **yes** | `0` | wrong — reported unused |
| `ProbeCoordToWorldPos[6]` | 96 | yes | `(D3D_SVF_USED)` | correct |
| `SkyLightColor` | 192 | **no** | `(D3D_SVF_USED)` | wrong — the reported symptom |

`WorldPosToProbeCoord` is also an unreported false negative: a caller could skip uploading a
constant the shader reads.

Changing exactly one character sequence in the shader, `ProbeIndex - 1` → `ProbeIndex` in

```hlsl
uint3 SourceProbeCoord = WorldPosToProbeCoordIndex(ProbePos + 0.5f, ProbeIndex - 1);
```

makes all three flags correct (`USED`, `USED`, `0`), with the `$Globals` layout unchanged. The
negative index is the trigger, exactly as reported.

**Root cause** — the analysis in the report holds up. `GetCBOffset`
(`lib/HLSL/DxilCondenseResources.cpp`) returns `unsigned` and folds `add i32 %ProbeIndex, -1`
to `0 + 0xFFFFFFFF`, which the caller shifts to `0xFFFFFFF0`. `MarkCBUse` then does
`upper_bound(offset)`, which returns `end()` for an offset past every field, and `it--`, so it
lands unconditionally on the last field. The same fold is why the intended field at offset 0
is never marked: one mis-folded offset, two wrong answers in opposite directions. A fix that
only stops marking the last field would still leave a genuinely-read field reported unused.

**History** — measured across all 20 stable releases, v1.4.1907 through v1.9.2607, holding the
reflection reader fixed and also re-checking with each release's own `dxcompiler.dll` (both
agree on every release):

- `WorldPosToProbeCoord` reported unused: **every release**, including v1.4.1907.
- `SkyLightColor` reported used: absent on v1.4.1907, present on v1.5.2010 and on all 18
  releases since. Below validator version 1.5 reflection recomputes usage with a range test
  instead of reading the metadata bit, and a range test cannot mis-attribute an out-of-range
  offset. No specific commit is named — compiling with `-validator-version 1.4` on `main`
  today does *not* restore the old behaviour, so the difference is not just that gate.

Not reproducible on Compiler Explorer: the flag lives in the container's reflection (`STAT`),
and the `-Fc` disassembly CE shows does not carry it.

Suggest keeping this open. Four years on it is unfixed, still reproduces, and the second face
above means the impact is wider than the title suggests.

**Labels:** keep `reflection`; suggest adding `bug` and `correctness`.

<sub>Compiler was built from `main` at `13730886e`; the local build self-reports a different
short SHA (`ab5400907`) because it was built from a fork of the same tree.</sub>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
