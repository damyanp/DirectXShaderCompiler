# Expected symptom — #5184 "WaveMatch with a vector input value"

Issue body: `WaveMatch(uint4 val)` — per the SM6.5 spec, `WaveMatch`'s argument "can be any
expression which evaluates to any of the currently supported primitive data types (e.g.
float4, uint2, etc.)". The reporter compiled a shader calling `WaveMatch` on a `uint4` value
and got a **DXIL validation error**:

```
error G315CBA34: Instructions must be of an allowed type.
note: at '%1219 = insertvalue %dx.types.fouri32 %1214, i32 %1218, 0' in block '#33' of function 'main'.
```

The reporter states this only happens **in debug mode (optimizations disabled + debug info
enabled)** — i.e. `-Od -Zi` (or equivalently `dxc`'s "Debug" preset). Under an optimized/release
build the error is silent — reporter suspects this doesn't mean it *works*, only that the
malformed IR gets folded/eliminated before validation sees it.

Comment (pow2clk, maintainer/collaborator, 2023-10-31): confirms via a Compiler Explorer repro
that "the value isn't getting scalarized. Might need a custom scalarization pass for
non-optimized builds." Their linked repro (https://godbolt.org/z/xjxe85z7z) actually uses a
`float4` input at `-O0 -T ps_6_6`, not `uint4` — so the defect is a general
"argument not scalarized under -Od" issue, not one specific to integer vectors. `WaveMatch`
itself always *returns* `uint4` (hence `%dx.types.fouri32` appearing even for a `float4`-typed
input), so this is not by itself proof the input type shape matters — that needs checking with
both `uint4` and `float4` inputs.

Comment (damyanp, Microsoft/DXC maintainer, 2024-09-19): "We expect that this will not be an
issue in clang; setting to dormant in case someone wants to tackle fixing this in DXC." — a
statement about project priority (deferred/dormant), not a claim the bug is fixed in DXC itself.
No `dormant` label exists on the live issue (only `bug`), so this is a triage-board disposition,
not a durable GitHub label; do not report it as resolved.

## What "this reproduces" means here

Compiling a shader that calls `WaveMatch` on a vector value (`uint4`, matching the reporter's
exact case, and `float4`, matching the maintainer-supplied repro) at `-T ps_6_6 -Od -Zi -E main`
(shader model >= 6.5, optimizations disabled, debug info enabled) must:

1. **repro**: fail DXIL validation with an "Instructions must be of an allowed type" /
   `insertvalue ... %dx.types.fouri32` (or `fourf32` for float) diagnostic — i.e. the malformed
   IR the reporter saw; or an internal compiler failure of the same shape.
2. **does-not-repro**: compile and validate cleanly, i.e. dxc emits well-formed DXIL for a
   vector-typed `WaveMatch` argument under `-Od`.

Repro quality: **complete** — issue names the exact intrinsic, argument type, exact flag
combination (unoptimized + debug info) and quotes the exact validator diagnostic. A maintainer
comment supplies an independently authored Compiler Explorer repro corroborating the shape (with
`float4` rather than `uint4`).

Secondary question raised explicitly by the reporter ("I even doubt whether dxcompiler really
allows and has implemented uint4 val following the spec"): does an **optimized** build (`-O3`,
i.e. no `-Od`) produce *correct*, not just clean, DXIL for the same input? This needs the same
predicate run without `-Od` as a control, not as the primary probe — a clean validator pass
under optimization does not by itself establish correctness of the returned per-lane match
value, and this triage does not have GPU execution evidence to settle that; it is
`not-compiler-verifiable` at the level of "is the result numerically correct", but "does the
compiler even emit clean DXIL for it" is answerable.
