> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3362](https://github.com/microsoft/DirectXShaderCompiler/issues/3362).

The actionable gap here appears to be diagnostics and documentation:
`-pack-optimized` silently assumes that connected stages use the same option and an identical
interstage signature.

The attached disassemblies record the command line that produced each one. The domain-shader
dump includes `-pack-optimized`; the pixel-shader dump named `pixel_pack_optimized` does not.
The two quoted tables were therefore produced under different packing rules.

Rebuilding the shaders from the struct in the report, with the flag on **both** stages, the two
signatures come out identical on `main` (`13730886e`):

```
ds_6_0  -pack-optimized     Output signature:
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; PREVIOUSPOSITION         0   xyzw        0     NONE   float   xyzw
; SV_Position              0   xyzw        1      POS   float   xyzw
; SV_ClipDistance          0      w        2  CLIPDST   float      w
; NORMAL                   0   xyz         2     NONE   float   xyz

ps_6_0  -pack-optimized     Input signature:
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; PREVIOUSPOSITION         0   xyzw        0     NONE   float   xyzw
; SV_Position              0   xyzw        1      POS   float
; SV_ClipDistance          0      w        2  CLIPDST   float      w
; NORMAL                   0   xyz         2     NONE   float   xyz
```

Compiler Explorer, three panes over one source: <https://godbolt.org/z/a1hKP6Tvs> — panes 1 and
2 are the DS and the PS with the flag (`SV_ClipDistance` at register 2, mask `w` in both, on two
compiler versions years apart); pane 3 is the same PS without the flag, and it is the table
quoted in this issue.

A whole `VS → HS → DS → PS` pipeline built the same way also agrees at every stage, including
the patch-constant signature, so nothing here is specific to domain shaders. The same holds on
all 20 stable releases back to v1.4.1907 (2019-07) — there is no regression to bisect. (That
release rejects `-pack-optimized` but accepts `-pack_optimized` and `/pack-optimized`.)

Two conditions have to hold, and the second is easy to miss:

1. **Pass `-pack-optimized` to every stage in the PSO**, not just one.
2. **The interstage signature must be identical**, not merely compatible. The pixel-shader table
   in the report has three elements where the domain shader emits four (no `NORMAL`). Optimized
   packing is a global optimisation over the whole element list, so removing one element moves
   the others: with the flag on both stages, the 4-element DS gives `SV_ClipDistance` register 2
   mask `w` while a 3-element PS gives register 2 mask `x`. This is what
   *"assuming identical signature provided for each connecting stage"* in the flag's help text
   is asking for. Unused interstage members must still be declared in the consuming stage's
   input struct — which is what sharing the struct through a header is meant to guarantee.

DXC gives no diagnostic when either condition is broken; the failure surfaces only at
`CreateGraphicsPipelineState`, as it did here. Whether it should is a design decision for the
maintainers. Two smaller gaps back it up: for DXIL the flag's contract exists only as the
one-line `--help` string (`docs/SPIR-V.rst` documents the SPIR-V behaviour), and the three
`pack_optimized` regression tests are all `vs_6_0`, single stage, with no test that two
connected stages agree.

I did not rerun D3D12 PSO creation; the compiler-verifiable result is that matching options and
matching structs produce matching signatures. The remaining work is therefore a diagnostic, a
documented contract, or connected-stage hull/domain test coverage. That evidence supports
reclassifying this from `bug` to `usability`/`docs`/`diagnostic`, subject to maintainer context.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
