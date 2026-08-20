# Expected symptom — #5169 "Add D3D_SVC_BIT_FIELD to D3D_SHADER_VARIABLE_CLASS"

## What the issue asks for

Follow-up to PR #5142 (which taught DXC's reflection to describe HLSL bitfield
members as `D3D_SVC_BIT_FIELD`). The reporter (python3kgae, a DXC maintainer)
states the actual ask precisely in the issue body:

> DXC is essentially casting an integer value to `D3D_SHADER_VARIABLE_CLASS`
> because the D3D headers haven't been updated with the new value. So this is
> tracking work to modify the D3D headers appropriately.

So the request is **not** "make reflection report bitfields correctly" (#5142
already did that) — it is "stop doing it via a local workaround cast and
instead have `D3D_SVC_BIT_FIELD` be a real enumerator of the public
`D3D_SHADER_VARIABLE_CLASS` enum in the D3D headers DXC builds against."

## This reproduces (is still open) if

- `external/DirectX-Headers/include/directx/d3dcommon.h`'s
  `D3D_SHADER_VARIABLE_CLASS` enum still stops at `D3D_SVC_INTERFACE_POINTER`
  and has no `D3D_SVC_BIT_FIELD` member, **and**
- DXC's own source (`lib/HLSL/DxilContainerReflection.cpp`,
  `lib/DxilContainer/D3DReflectionStrings.cpp`) still unconditionally
  `#define`s `D3D_SVC_BIT_FIELD` as
  `((D3D_SHADER_VARIABLE_CLASS)(D3D_SVC_INTERFACE_POINTER + 1))`, i.e. still
  carries the `FIXME: remove the define once D3D_SVC_BIT_FIELD added into
  D3D_SHADER_VARIABLE_CLASS` workaround from #5142 verbatim.

## This is fixed if

The vendored D3D headers declare `D3D_SVC_BIT_FIELD` as a first-class
`D3D_SHADER_VARIABLE_CLASS` enumerator (matching the value DXC already
synthesizes), and the `#define`/`#ifdef ADD_SVC_BIT_FIELD` workaround and its
FIXME comment have been removed from DXC's own sources because they are no
longer needed.

## Repro quality

`none` — the issue is a request to change a vendored public header, not a
compiler behavior bug. There is no HLSL input whose compiled output would
differ before/after a fix; `dxc`'s bitfield-reflection *behavior* already
matches the reporter's own PR #5142 and is not what is being asked to change.
The evidence is source-level: whether the enumerator has been added to the
header, and whether DXC's local workaround has been retired. See `notes.md`.

This makes the issue `not-compiler-verifiable` in the sense the skill defines:
no `dxc` invocation over any shader can distinguish "fixed" from "not fixed"
here, because both states produce byte-identical reflection output (DXC
supplies the numeric value itself either way). The producing instrument is
the header file, not a compile.
