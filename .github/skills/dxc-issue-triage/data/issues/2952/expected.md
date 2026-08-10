# #2952 — Expose ray payload size / function type through Reflection

**Written before running any compiler or harness.** Filed 2020-06-08 by `Kinslore`.
Label: `reflection`. Two follow-up comments, both by `damyanp` (2024-04-11, 2024-06-27),
asking `@tex3d` whether this is possible today and saying that if not, it should become a
feature request. `@tex3d` has not answered in the thread.

## The report, in full

> Currently, I could not find any way to retrieve a payload size or a function type
> (raygen, miss...) from a ReflectionContainer. Having this kind of information would be
> helpful in some situations, would it be possible to expose it ?

## Repro quality

`prose-only`. There is no shader, no code, no command line and no API transcript. The
reporter names one API concept ("ReflectionContainer" — almost certainly
`IDxcContainerReflection`, the interface a DXR application uses to reflect a compiled
`lib_6_3` container) and two pieces of data they could not find:

1. **ray payload size** — the byte size of the user payload struct a raytracing shader
   declares (the `RayPayload` parameter of a miss/anyhit/closesthit shader).
2. **function type** — which raytracing shader kind an exported function is
   (`raygeneration`, `miss`, `closesthit`, `anyhit`, `intersection`, `callable`).

Any repro is therefore **agent-constructed**: a DXR library containing one function of
each kind with a payload of known size, plus a program that asks the reflection API for
those two facts. The construction is faithful to the report as long as the API it drives
is the one an application actually has (`IDxcContainerReflection` +
`ID3D12LibraryReflection` / `ID3D12FunctionReflection`), not a DXC-internal one.

## What "this reproduces" means

**Reproduces** if, on current `main`, an application holding a compiled DXR library
container and using the public reflection API:

- **(a)** cannot obtain the ray payload size of any entry, and
- **(b)** cannot obtain the shader kind of an exported function

— i.e. `ID3D12FunctionReflection::GetDesc`'s `D3D12_FUNCTION_DESC` contains neither a
payload-size field nor an interpretable shader-kind field, and no other method on the
`ID3D12LibraryReflection` / `ID3D12FunctionReflection` pair returns them.

**Does not reproduce** if either fact is retrievable today through that API. Because this
is a two-part request, a **partial** answer is a real and likely outcome and must be
reported as `changed-behavior` rather than forced to either pole: e.g. if the shader kind
turns out to be encoded in `D3D12_FUNCTION_DESC.Version` (DXC does write a shader-kind
value into that field for non-library shaders) while payload size is still unavailable,
then half the request is already satisfied and the issue text is out of date on that half.

## Predictions to check, written down now so they cannot be back-fitted

These are stated *before* looking at the compiler's answer so that whichever way they
land, the write-up is falsifiable.

- **P1.** `D3D12_FUNCTION_DESC` (`external/DirectX-Headers` / `d3d12shader.h`) has **no**
  payload-size or attribute-size field at all. It is a D3D11-era function-reflection
  struct predating DXR. If so, exposing payload size cannot be done by populating an
  existing field — it needs either a new interface or a new struct, which is why this
  request has sat for five years.
- **P2.** `D3D12_FUNCTION_DESC.Version` will be **non-zero and will encode the shader
  kind**, because DXC's shader reflection encodes `(kind << 16) | (major << 4) | minor`.
  If it does, "function type" is *already* retrievable, just undocumented and awkward.
  If it is zero or constant across kinds, the report stands on both halves.
- **P3.** The **data exists in the container** even if the API does not expose it: the
  RDAT part (`RuntimeDataFunctionInfo`, `lib/DXIL/RDAT_*`,
  `include/dxc/DxilContainer/RDAT_LibraryTypes.inl`) is expected to carry a shader-kind
  field and, for raytracing entries, payload/attribute sizes. This is the load-bearing
  check: **if the data is not in the container at all, then no reflection API change
  alone can expose it**, and the request is really "record this in the container", which
  is a substantially different (and larger) piece of work. Check current `main`, not
  memory — RDAT has gained fields since 2020, so a field's presence today says nothing
  about whether it was there when the issue was filed.

## Symptom predicate, in words

The harness compiles a DXR library and walks the same interfaces the reporter would.
It reproduces when **both** of these hold in one transcript:

- the walk **completed** (the container loaded, `ID3D12LibraryReflection` was obtained,
  and `ID3D12FunctionReflection::GetDesc` returned `S_OK`) — a positive anchor, so that a
  failed compile or an aborted walk cannot satisfy an absence clause for free; and
- the transcript reports **no payload size** available from `D3D12_FUNCTION_DESC` for a
  raytracing entry whose payload size is known by construction.

The function-type half is recorded as a measured value rather than as a match clause,
because P2 may well make it a non-symptom, and folding a possibly-satisfied half into the
predicate would make the whole issue score as fixed or as broken on the strength of the
other half alone.

## History

`bisect` **cannot** be used. This defect is an API surface, not anything `dxc.exe` prints,
so a release sweep that substitutes each release's `dxc.exe` would score every release
`no-repro` and report a confident "never reproduced" — the inverse of the truth. The
history must be measured by pointing the harness at each release's `dxcompiler.dll`,
which is where the reflection implementation lives.

The interesting historical question is **not** "when did this break" (nothing is broken;
nothing was ever implemented) but **when, if ever, the underlying data appeared in the
container** — because that is what would date any future implementation of the request.

## What would make this `not-compiler-verifiable`

Nothing, if the reflection API is reachable from a harness: the code under test lives in
`dxcompiler.dll`, which every release ships, and needs no GPU, device or driver. Only if
the reporter turned out to mean a D3D12 *runtime* reflection path would the compiler stop
being the instrument.

## Expected disposition

This is a **feature request**, not a bug, so `suggested-action` is most likely
`enhancement-not-bug` and the label proposal should be checked for a routing label that
says so. `close-fixed` is only available if both halves turn out to be retrievable today.
