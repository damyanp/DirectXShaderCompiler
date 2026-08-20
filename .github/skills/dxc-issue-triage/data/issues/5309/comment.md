> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5309](https://github.com/microsoft/DirectXShaderCompiler/issues/5309).

Tested against a Debug build of `main` (commit `89e2f98e2`). `dxbc2dxil`/`dxilconv` are not
executable in this environment (see below), so this is a source-level analysis rather than a
repro run.

`0x8007007e` is `HRESULT_FROM_WIN32(126)`, and Win32 error 126 is `ERROR_MOD_NOT_FOUND` ("the
specified module could not be found"). In `dxbc2dxil.cpp`, the only call that returns
`HRESULT_FROM_WIN32(GetLastError())` is `Converter::GetDxcCreateInstance`, called from
`CreateDxbcConverter` to `LoadLibraryExW(L"dxilconv.dll", NULL,
LOAD_LIBRARY_SEARCH_APPLICATION_DIR)` — and this runs **before** the DXBC bytes are ever passed
to `converter->Convert()`. A standalone harness reproducing that exact API call against a
guaranteed-missing module confirms the match:

```
LoadLibraryExW("missing", LOAD_LIBRARY_SEARCH_APPLICATION_DIR):
  GetLastError() = 126 (0x0000007E)
  HRESULT_FROM_WIN32(GetLastError()) = 0x8007007E
```

In other words, this specific error most likely means `dxbc2dxil.exe` could not find
`dxilconv.dll` next to it — not that the DXBC content failed to convert. The attached DXBC
(`0.txt`) is well-formed (correct `DXBC` fourcc, and its `TotalSize` field matches the file's
exact byte length), so the content itself doesn't look like the problem.

A plausible path is selective build/deployment: default builds put `dxbc2dxil.exe` and
`dxilconv.dll` together, but `dxbc2dxil` has no CMake dependency on `dxilconv`, so building or
copying only the `.exe` can produce this exact `0x8007007E` symptom.

This environment can't run the actual conversion to check either explanation further:
`dxilconv` isn't built here (`HLSL_BUILD_DXILCONV=OFF`, and no `dxbc2dxil.exe`/`dxilconv.dll`
exist anywhere in this build tree), and no published release ships these binaries either.

If `dxilconv.dll` was present next to `dxbc2dxil.exe` and this still failed, that would point to
a real `DxbcConverter` defect. Suggest `needs repro steps` alongside `dxilconv` to capture that
missing confirmation.

---
<sub>Triaged with AI assistance. `dxbc2dxil`/`dxilconv` are not built in this environment, so no
compiler output was produced; the evidence is source reading plus a standalone Win32 API
harness reproducing the exact error code outside any DXC build target. Please flag anything
that looks wrong.</sub>
