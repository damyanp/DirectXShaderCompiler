> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3066](https://github.com/microsoft/DirectXShaderCompiler/issues/3066).

Still current. Checked against `main` at `13730886e` (a local Debug build reporting
`1.9.0.5433`; it self-reports a different, fork-local commit hash) and against all 20 stable
releases from `v1.4.1907` to `v1.9.2607`.

The five requests don't all land the same way, so taking them one at a time. Line references
are to the disassembly of a small pixel shader that exercises all of them at once
(`Texture2D` sample, `cbuffer` load, `max(x, 0.0001)`, `RWStructuredBuffer` store).

**Float constants in the comment (2nd bullet) — unchanged.** The listing still prints your
example almost verbatim:

```
%16 = call float @dx.op.binary.f32(i32 35, float %15, float 0x3F1A36E2E0000000)  ; FMax(a,b)
```

The comment decodes the opcode and names the operands, then stops; `0.0001` appears nowhere.

**Resource names on loads and stores (4th bullet) — unchanged, and there's an open `TODO`
for it.** `printInfoComment` in `tools/clang/tools/dxcompiler/dxcdisassembler.cpp` carries
`// TODO: if an argument references a resource, look it up and write the name/binding`. That
comment was already in the file when this issue was filed and is still there.

**Output Dependencies (5th bullet) — unchanged.** Still bare element indices on both sides:

```
;   output 0 depends on inputs: { 4, 5 }
```

**Resource Bindings (also 5th bullet) — already does what you asked**, and did in 2020; the
table prints `g_diffuseTexture … T0 … t0`. That half looks satisfied.

**Source locations (1st bullet) — partly there.** With `-Zi -Qembed_debug` every instruction
gets `; line:N col:M` and debug-value comments get `var:"…" func:"…"`. No file name and no
source snippet, and nothing without `-Zi`.

**On the `dx.op.storeOutput.f32` example (3rd bullet)** — worth flagging in case it changes
what you'd want: that opcode is decoded, and was in 2020 —
`; StoreOutput(outputSigId,rowIndex,colIndex,value)`. The op-name table is generated from
hctdb for every op, so it has never been limited to unary/binary. What is still missing is
decoding the operand *values*: `outputSigId` isn't resolved to `SV_Target`, and `i8 0` isn't
resolved to `.x`. If that's the substance of the bullet then it stands as written.

**One thing that has moved, and one that moved backwards.**

On SM 6.6+, `annotateHandle` now decodes the resource properties inline —
`; AnnotateHandle(res,props)  resource: Texture2D<4xF32>` — which is the shape the 3rd bullet
asks for.

Going the other way: in `v1.4.1907` the default listing printed resource-derived value names
with no debug flag, e.g. `%dx.types.Handle %g_luminanceOut_UAV_structbuf`. From `v1.5.2010`
onward that same command prints `%dx.types.Handle %1`, and the names only come back with
`-Zi -Qembed_debug`. Bisected over the 20 releases with two independent predicates; the
transition is in that one window both times. I could not find the mechanism — the handle name
is built unconditionally in `DxilCondenseResources.cpp` — so please treat that as an
observation rather than a diagnosis. Net effect is that default disassembly gives *less* of
the 4th bullet than it did in 2019.

Compiler Explorer: https://godbolt.org/z/e69hs8h97 — `dxc_1_6_2112` and trunk, identical text
at all three places. One caveat: Compiler Explorer adds `-Zi -Qembed_debug` to every DXC pane
whatever you type (visible in `!dx.source.args`), so those panes show the compiler at its most
readable, not its default. The named handles you'll see there are *not* what a plain command
line prints.

For contrast, `dxa -dumpreflection` on the same shader already prints
`SystemValueType: D3D_NAME_POSITION`, `Type: D3D_SIT_CBUFFER`, `Name: g_luminanceOut`. The
enum-to-name tables exist in the reflection printer; the disassembly printer just doesn't use
that kind of decoding.

Suggested labels: keep `enhancement` and `dxil`, add `usability`. This is a live enhancement
request, not a bug — nothing here is incorrect output.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
