# Expected behaviour (written before running anything)

Issue: DXC possibly emitting spurious `[-Wpayload-access-trace]` PAQ warnings in SM 6.7.

## What the reporter says

A `[raypayload]` struct declares two members `ddxRay` and `ddyRay` as
`read(anyhit) : write(caller)`. The raygeneration shader writes both members
directly (`payload.ddxRay = ...; payload.ddyRay = ...;`) and then calls a
**helper function** `TraceRadianceRay(ray, payload)` — taking the payload as
an `inout` parameter — which itself calls `TraceRay(...)` on that parameter.

DXC emits, for each of the two members:

```
warning: field 'ddxRay' is 'write' for 'caller' stage but field is never written for TraceRay call [-Wpayload-access-trace]
warning: field 'ddyRay' is 'write' for 'caller' stage but field is never written for TraceRay call [-Wpayload-access-trace]
```

The reporter's claim is that this is wrong: the fields *are* written, just in
the calling function rather than in the function that lexically contains the
`TraceRay` call.

## What "reproduces" means here

The repro quality is `agent-constructed`: the reporter attached only inline
code fragments plus a link to an external multi-file game-engine repo
(`https://github.com/MaicoDeBlasio/Win32GameDR.git`), not a compilable
single-file HLSL shader. A best-effort single-file repro has to be built
that preserves the structural feature the report calls out: a `write(caller)`
field is written in one function, and the `TraceRay` call that is supposed to
"see" that write is textually inside a *different* function that receives the
payload as an `inout` parameter.

This reproduces if: compiling a `lib_6_7` (or `lib_6_6`, since PAQs are not
SM-6.7-specific — the title says "in SM 6.7" but the feature predates it)
shader with `-enable-payload-qualifiers` where
  1. a raygeneration shader writes a `write(caller)`-qualified field directly,
  2. then calls a non-shader function `Trace(...)` that takes the payload as
     `inout` and calls `TraceRay` inside it,
produces the `field '<x>' is 'write' for 'caller' stage but field is never
written for TraceRay call` warning for that field.

This does **not** reproduce (or is a different/narrower bug) if the warning
only appears when the write and the `TraceRay` call are in the same function,
matching `nested_access.hlsl`'s existing `TEST_NUM=5` coverage — that
configuration is already covered by the test suite and is not what the
reporter describes.

Note the existing regression-test file
`tools/clang/test/HLSLFileCheck/hlsl/payload_qualifier/nested_access.hlsl`
already has a `TEST_NUM=3` block (`foo`/`foo_in`/`foo_out`) that intentionally
tests write-then-read propagation through a helper taking the payload as a
parameter, but that block is about ordinary field read/write tracking within
`closesthit`, not about a `TraceRay` call living inside the helper. No existing
test combines "helper function contains the `TraceRay` call" with "caller of
the helper wrote a `write(caller)` field first" — the exact shape of this
report.

By default `-enable-payload-qualifiers` is required to opt in to payload
qualifier diagnostics at all (see `access.hlsl`'s `-enable-payload-qualifiers`
flag on every RUN line); the reporter's command line does not pass it, which
is itself worth checking against the actual compiler default before treating
the missing flag as inert.
