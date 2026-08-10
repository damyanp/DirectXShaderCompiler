# #2952 — Expose ray payload size / function type through Reflection

Reported 2020-06-08 by `Kinslore`; label `reflection`; still open. Two
comments, both by `damyanp` (2024-04-11 and 2024-06-27), asking `@tex3d`
whether this is already possible. That question was never answered, and this
triage answers it.

Ground truth compiler: `main-debug`, a clean Debug build. It self-reports
`1.9.0.5433 (triage, ab5400907)`; `ab5400907` is a fork-local SHA that does not
resolve publicly, so everything below is cited against **`13730886e`**, the
upstream `main` commit whose compiler source is byte-identical to this build
(`git diff --name-only ab5400907 13730886e` → 597 files, **0** outside
`.github/skills/dxc-issue-triage/`; the control, `13730886e~200`, differs in
581 files outside that directory, so the comparison is not vacuous).

## Verdict in one line

The request still stands, but it is half stale and its cheap half is already
done: **the shader kind is retrievable today** from
`D3D12_FUNCTION_DESC.Version`, and **the payload size is already recorded in
the container** and has been since 2018 — what is missing is only a supported
way to read it. This is an API-surface request, not a data-capture request.

## What the issue asks for

> Currently there doesn't seem to be a way to get the ray payload size out of a
> compiled library, or to tell whether a given function is a raygen, miss,
> closesthit... — it would be useful to expose this through reflection.

Two separable asks:

* **Q1 — function type.** Given `ID3D12FunctionReflection`, can a caller learn
  that a function is raygeneration / miss / closesthit / anyhit / intersection
  / callable?
* **Q2 — payload size.** Can a caller learn the ray payload (and attribute)
  size in bytes?

## Answers

### Q1: yes, already — but only *de facto*

`CFunctionReflection::GetDesc` sets

```
pDesc->Version = EncodeVersion(kind, pSM->GetMajor(), pSM->GetMinor());
```

— `lib/HLSL/DxilContainerReflection.cpp:2848`, where `kind` comes from
`DxilFunctionProps::shaderKind`. `EncodeVersion`
(`include/dxc/DxilContainer/DxilContainer.h:603`) packs it as
`(kind << 16) | (major << 4) | minor`, so `D3D12_SHVER_GET_TYPE(Version)` hands
back the raytracing shader kind directly. Measured on all seven functions in
the repro, on every release tested: 7 RayGeneration, 8 Intersection, 9 AnyHit,
10 ClosestHit, 11 Miss, 12 Callable, and 6 Library for the plain non-entry
export. Seven of seven agreed with what the container itself records.

**The catch, and it is the whole reason the issue reads as unanswered.**
`d3d12shader.h` defines `D3D12_SHADER_VERSION_TYPE` only up to 5
(`D3D12_SHVER_COMPUTE_SHADER`). Values 6–15 are `hlsl::DXIL::ShaderKind`, DXC's
own enum, and appear in no shipped header. DXC's own dumper has to reach for
the internal enum to print them — `D3DReflectionDumper::DumpShaderVersion`
casts `D3D12_SHVER_GET_TYPE(Version)` to `hlsl::DXIL::ShaderKind`
(`lib/DxilContainer/D3DReflectionDumper.cpp:29` and `:160`). So an application
*can* get the right answer, but only by hardcoding constants it was never
given. Q1 is therefore a documentation/header gap, not a missing capability.

### Q2: the data exists; the *reader* does not ship

The container already carries it. `RuntimeDataFunctionInfo` in the RDAT part
declares:

```
include/dxc/DxilContainer/RDAT_LibraryTypes.inl:205  RDAT_VALUE(uint32_t, PayloadSizeInBytes)
include/dxc/DxilContainer/RDAT_LibraryTypes.inl:207  RDAT_VALUE(uint32_t, AttributeSizeInBytes)
```

written by `lib/DxilContainer/DxilContainerAssembler.cpp:1329` and `:1342`.
A repository-wide `git log --all -S PayloadSizeInBytes` dates the field to
commit **`0a098d7cb`, 2018-02-26** — more than two years before the issue was
filed and before every release that can be probed. A path-scoped search starts
later, after the RDAT types moved, and gives the wrong introduction commit. It
is also in the DXIL itself: `dx.entryPoints` entry
properties use tag 6 for the ray payload size and tag 7 for the attribute size
(`include/dxc/DXIL/DxilMetadataHelper.h:305-306`), visible in any `-T lib_6_3`
disassembly.

But `D3D12_FUNCTION_DESC` has **no field that could hold it**. The harness
enumerates all 31 numeric fields of the struct and searches them for the
payload size the container reports; on every release, for every function, it
finds nothing. There is no near-miss and no partially-populated field — the
struct simply has no such member, so this cannot be fixed by populating
something that already exists.

And the RDAT reader is not shipped. Release packages contain only:

| release | `inc/` |
| --- | --- |
| v1.4.1907 | *(no `inc/` at all)* |
| v1.5.2003 – v1.7.2207 | `d3d12shader.h`, `dxcapi.h` |
| v1.7.2212 – v1.8.2407 | + `dxcerrors.h`, `dxcisense.h` |
| v1.8.2505 – v1.9.2607 | + `dxcpix.h`, `Support/ErrorCodes.h`, `inc/hlsl/…` |

`DxilRuntimeReflection.h`, `DxilRuntimeReflection.inl` and
`RDAT_LibraryTypes.inl` — the headers this triage's own harness had to include
to read the payload size — are in none of them. An application can retrieve the
raw bytes with `IDxcContainerReflection::GetPartContent(DFCC_RuntimeData)` and
then has nothing supported to parse them with. (Full listing in
`manual-case-ground-truth-witnesses.txt`, section 3.)

So the ask reduces to a choice between: add fields to a struct owned by the
D3D12 headers; add a DXC-specific reflection interface; or ship the RDAT
reader. That is a product decision and this triage does not take it.

## What was measured

**`dxc.exe` cannot express any of this** — there is no command line that asks a
reflection question. So the probe is `refl2952.exe`, built from `refl2952.cpp`
in this directory and registered as compiler `main-debug-refl2952`. It compiles
the shader through `IDxcCompiler::Compile`, then walks
`IDxcContainerReflection` → `ID3D12LibraryReflection` →
`ID3D12FunctionReflection`, and separately reads the RDAT part. All of that
executes inside `dxcompiler.dll`, so pointing `DXC_REFLECT_DLL` at a release's
DLL tests that release's reflection implementation, not the harness's.

Design points that matter for trusting the result:

* It reads **RDAT first** and searches the API fields for the size the
  *container* reported, rather than for a hardcoded 28. That is why
  `control-payload-16.hlsl` (16-byte payload) works with no harness edit.
* `RESULT:` is printed only after a complete walk. Any earlier failure prints
  `refl2952: WALK-INCOMPLETE: …` and exits 2, so "no payload found" can never
  be produced by a walk that silently stopped early.
* A **field-search self-test** runs every time: it searches the same field
  table for `BoundResources`' own value and must find the `BoundResources`
  field. `SELFCHECK: field-search-selftest=pass` is a required clause of
  `match.json`, so a reader that had quietly stopped searching would score
  `no-match`, not a false `repro`.
* The reflection function list is cross-checked against the RDAT function list
  by mangled name; a mismatch emits `PARSE-WARNING`.
* `Version` is excluded from the payload-size field search, since it holds the
  encoded kind and could collide numerically for no meaningful reason.

### Ground truth

```
RESULT: API-SHADER-KIND=available API-PAYLOAD-SIZE=unavailable RDAT-SHADER-KIND=present RDAT-PAYLOAD-SIZE=present
SELFCHECK: field-search-selftest=pass
SUMMARY: payload-carrying-entries=4 api-payload-found=0 kind-checked=7 kind-agrees=7
```

### Controls

| shader | expectation | result |
| --- | --- | --- |
| `repro.hlsl` — one entry of every DXR 1.0 kind | match | match |
| `control-payload-16.hlsl` — same shape, 16-byte payload | match | match (predicate is not tied to the number 28) |
| `control-nonrt-lib.hlsl` — library with no raytracing entries | no-match | no-match (`payload-carrying-entries=0`) |
| `control-compute.hlsl` — `cs_6_0` | no-match | no-match, exit 2 |

The `nonrt` control is the one that matters: without it, "no payload found in
the API" would be satisfied by a shader that has no payload to find. It scores
`no-payload-entries` on *every* release, so the predicate can never match
vacuously. The compute control aborts at "no RDAT part in this container",
before the library-reflection step — a `cs_6_0` container has no RDAT — which
is a different failure mode from the library controls and is recorded as such.

### History — 22 captured builds, hand-written matrix

`manual-case-release-matrix.txt`, produced by `measure.py --history`. Every one
of the 20 stable releases from v1.4.1907 through v1.9.2607 gives:

```
pay-entries=4   api-kind=available   api-pay=unavailable   rdat-pay=present
```

The same result holds for `main-debug` and for a separately measured
`v1.5.2003` prerelease: 22 of 22 captured builds `repro`, and all 22 `nonrt`
controls report `no-payload-entries`, with no invalid probes. The prerelease is
supplemental because the issue does not explicitly name it; the formal history
claim is the 20-stable-release matrix. **Never regressed, never worked in a
tested stable release** — and the RDAT field predates all of them.

**`triage.py bisect` was NOT run, deliberately.** `bisect` substitutes each
release's `dxc.exe` for the registered compiler. `dxc.exe` never calls
`ID3D12LibraryReflection`, so every release would score `no-repro` and the tool
would report a confident "never reproduced in any release" — the exact inverse
of the truth. The matrix above replaces it by holding the harness fixed and
varying `DXC_REFLECT_DLL`.

### Independent witnesses

`manual-case-ground-truth-witnesses.txt` re-asks both questions with tools that
share no code with the harness:

* `dxa -dumpreflection` walks `ID3D12LibraryReflection` through DXC's own
  `D3DReflectionDumper` and prints, for each function, `Shader Version: AnyHit
  6.3`, `Callable 6.3`, `Library 6.3` … — independent confirmation of Q1, from
  code that is not the harness. Its `D3D12_FUNCTION_DESC` block prints
  `Creator`, `Flags`, `RequiredFeatureFlags`, `ConstantBuffers`,
  `BoundResources`, `FunctionParameterCount`, `HasReturn` and nothing else:
  there is no payload size to print.
* `dxa -dumprdat` prints `ShaderKind`, `PayloadSizeInBytes` and
  `AttributeSizeInBytes` for every entry — confirming Q2's data is present.
* The `inc/` census above, which is metadata and not a reading of the container
  at all.

The `dxa` witnesses do share the RDAT *header* code with the harness (a
different binary, the same `.inl`), so they are not fully independent on the
RDAT half. The source citations and the `-T lib_6_3` metadata (which any
disassembler shows) carry that half instead.

## Compiler Explorer

https://godbolt.org/z/YT1q1cqjb — `dxc_1_6_2112` and `dxc_trunk`, both clean,
both showing the payload size and the shader kind in `dx.entryPoints`. CE
cannot call a reflection interface, so the link demonstrates only that the data
exists and has not changed; the API finding comes from the harness. See
`godbolt-note.txt`.

## Limitations

* The repro is agent-constructed. The issue contains no code, so "what the user
  actually wanted reflected" is inferred from its prose; a reporter with a
  different mental model (say, wanting the *maximum* payload size across a
  subobject-configured RTPSO rather than per-entry) would be asking something
  this repro does not measure. `RaytracingShaderConfig`'s
  `MaxPayloadSizeInBytes` (`DxilContainerAssembler.cpp:1617`) is a related but
  distinct piece of data that was not probed.
* Only the C++ `ID3D12*Reflection` path was tested. Anything layered on top of
  it inherits the same limitation, but that was not verified.
* Whether adding fields to `D3D12_FUNCTION_DESC` is even open to DXC — the
  struct is declared in `external/DirectX-Headers` — is a question this triage
  raises but does not answer.
