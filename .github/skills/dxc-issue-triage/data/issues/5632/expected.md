# Expected symptom (written before any probe is run)

Issue title: "Can construct-cast an array type to non-array without compiler complaining
(DXIL Crash)". The reporter's original repro is a construct-cast of a single-element array
member to a scalar, `float(lineStyles[45]._pad)` where `_pad` is `uint _pad[1u]` inside a
`StructuredBuffer<LineStyle>` element. Two distinct asks are bundled in the thread, and the
maintainer (llvm-beanz, comment 2023-08-31) explicitly separates them:

> The SPIR-V behavior here matches FXC ... DXC crashes when generating DXIL for this code ...
> So I think the only bug here is that DXC is crashing in DXIL, and we should probably issue a
> diagnostic on array->scalar truncation.

## Ask A — DXIL crash (the maintainer-confirmed bug)

Reported repro (maintainer's own godbolt link, `godbolt.org/z/97GMh3zjd`), compiled for DXIL
(no `-spirv`) with `-HV 2021 -T ps_6_7 -enable-16bit-types`: "DXC crashes when generating DXIL
for this code."

**Reproduces** = the ground-truth build exits with an internal failure (crash/assert/access
violation — see `match.json`, `internal_failure` kind) compiling `repro.hlsl` with the args in
`cmd.txt`.

**Does not reproduce** = the same command exits 0 (or with an ordinary diagnosed error) and
emits DXIL.

## Ask B — missing diagnostic on array->scalar truncation

Reporter's original repro (`godbolt.org/z/dqa1jG41b`), compiled for SPIR-V with
`-spirv -HV 2021 -T ps_6_7 -enable-16bit-types -fvk-use-scalar-layout -fspv-debug=source
-fspv-debug=tool`: no warning or error is printed for the array->scalar construct-cast, and
codegen silently behaves as `float(lineStyles[45]._pad[0])`.

The maintainer states this SPIR-V behavior "matches FXC" — i.e., is accepted/by-design on that
path — but proposes DXC "should probably issue a diagnostic" for the truncation generally.
This is an enhancement request, not a confirmed regression/bug in itself.

**Reproduces** (as an open request) = compiling the repro (SPIR-V and/or DXIL, where DXIL does
not crash) still emits no warning/error about the array->scalar truncation.

**Does not reproduce** = a diagnostic (warning or error) is now emitted for this construct.

## Repro quality

`complete` — both repros are taken verbatim from the issue thread's own godbolt links (the
reporter's `dqa1jG41b` and the maintainer's `97GMh3zjd`), which share the same HLSL source and
differ only in the compile target (`-spirv` vs DXIL).
