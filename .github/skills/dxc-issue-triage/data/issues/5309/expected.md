# Expected behavior for #5309

Title: Dxbc to Dxil conversion failure

## What the reporter claims

Running the `dxbc2dxil` command-line tool against a DXBC shader (attached as `0.txt`,
renamed from `.dxbc`/`.cso` -- confirmed below to have a well-formed `DXBC` fourcc header)
prints only:

```
Conversion failed - error code 0x8007007e.
```

and produces no DXIL output. The reporter has no HLSL source (only the FXC-compiled DXBC),
says they built the project "last week" and believes their build "included the fxc compiler,"
and asks to reopen after a maintainer (`llvm-beanz`) closed the issue for lack of information.
No further comment exists after the DXBC was attached (2023-06-30); the issue is currently
`OPEN`/`REOPENED`.

## What "reproduces" means here

`Conversion failed - error code 0x%08x.` is printed by `dxbc2dxil.cpp`'s `wmain` catch block
for *any* uncaught `hlsl::Exception` whose message is empty, formatted from `E.hr`. So
"reproduces" cannot mean just "some error with this code is printed" without first
identifying *which* code path inside `dxbc2dxil.cpp`/`DxbcConverter` produces HRESULT
`0x8007007e` specifically, because the tool has several unrelated ways to fail before ever
touching the DXBC content:

1. **Module-load claim (source-checkable without running the tool):** `0x8007007e` is
   `HRESULT_FROM_WIN32(126)`, and Win32 error 126 is `ERROR_MOD_NOT_FOUND` ("The specified
   module could not be found"). In `dxbc2dxil.cpp`, the only call that returns
   `HRESULT_FROM_WIN32(GetLastError())` is `Converter::GetDxcCreateInstance`, invoked from
   `CreateDxbcConverter` to `LoadLibraryExW(L"dxilconv.dll", NULL,
   LOAD_LIBRARY_SEARCH_APPLICATION_DIR)` -- and this call happens **before**
   `converter->Convert(pDxbcPtr, ...)` is ever reached, i.e. before the attached DXBC bytes
   are examined by the converter at all. This is `repros` (in the narrow, source-verifiable
   sense of "this is still how the tool can fail this way today") if `dxilconv.dll` still is
   loaded exactly this way at this exact point in `main`'s current source, and would be
   `does-not-repro` if that dynamic-load call had been removed or hardened (e.g. to print a
   clearer "converter module not found" message, or if `dxbc2dxil` now links `DxbcConverter`'s
   COM entry point directly instead of loading a same-named DLL).
2. **Genuine conversion-logic claim (would require executing `converter->Convert()` on the
   attached DXBC):** whether the DXBC itself, once the converter module *is* loaded, converts
   cleanly to DXIL or fails partway through `DxbcConverter`'s translation. This cannot be
   judged as `repros`/`does-not-repro` without running `dxbc2dxil.exe` end to end, which this
   environment cannot do (see below) -- it would be `not-compiler-verifiable` on its own for
   this claim specifically.

Given claim 1's mechanism is confirmed (see notes.md) and independently reproduced with a
tiny out-of-tree harness, and claim 2 cannot be executed here at all, the overall verdict is
recorded as `not-compiler-verifiable`: the reported symptom is very plausibly explained by an
absent `dxilconv.dll` next to the reporter's own `dxbc2dxil.exe` (a build/deployment condition
of the reporter's own machine, not a property of the DXBC content or of `DxbcConverter`'s
translation logic), and this environment cannot execute the actual conversion to check claim 2
regardless.

## What is *not* verifiable through `dxc.exe` or in this environment

- `dxc.exe`'s HLSL front end never calls `DxbcConverter` or loads `dxilconv.dll`; it has no
  code path relevant to this issue at all (same reasoning as #4786, a related `dxilconv` issue
  triaged in this batch).
- This checkout does not build `dxilconv` at all: `build/CMakeCache.txt` has
  `HLSL_BUILD_DXILCONV:BOOL=OFF`, and no `dxbc2dxil.exe` or `dxilconv.dll` exists anywhere
  under `build/` (confirmed by recursive search). Enabling it would require reconfiguring the
  shared CMake cache and building new targets in the shared `build/` tree, which this
  session's boundary explicitly prohibits (no rebuilds).
- No catalogued stable release ships `dxbc2dxil.exe` or `dxilconv.dll` either (per #4786's
  finding, which this triage does not re-derive independently but which is consistent with
  `dxbc2dxil` never being part of the public release archives).
- So end-to-end execution of the reporter's exact repro (their DXBC through a real
  `dxbc2dxil.exe`) is out of reach in this environment under any configuration, not only the
  currently-configured one.

Repro quality: **partial**. A real, well-formed DXBC attachment exists (the only artifact that
was ever provided, and the reporter has no HLSL to go with it), but the reported failure mode
plausibly never reaches the DXBC-dependent code at all, so the attachment's own content may be
irrelevant to explaining the reported error -- which is itself the main finding.
