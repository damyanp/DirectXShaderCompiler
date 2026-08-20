# Notes for #5309

## Summary

The reporter's `dxbc2dxil` conversion fails immediately with
`Conversion failed - error code 0x8007007e.`. That HRESULT is
`HRESULT_FROM_WIN32(ERROR_MOD_NOT_FOUND)` (Win32 error 126, "The specified module could not be
found"), and `dxbc2dxil.cpp`'s only call that surfaces `HRESULT_FROM_WIN32(GetLastError())` is
`Converter::GetDxcCreateInstance`'s `LoadLibraryExW(dllFileName, NULL,
LOAD_LIBRARY_SEARCH_APPLICATION_DIR)`, invoked by `CreateDxbcConverter` to load `dxilconv.dll`
-- **before** the DXBC bytes are ever passed to `converter->Convert()`. This is the same
generic-error-with-no-detail failure shape as #4786's `DxbcConverter`, but with an entirely
different underlying cause: this looks like a missing/unresolvable `dxilconv.dll` next to the
reporter's own `dxbc2dxil.exe`, not a bug in the DXBC-to-DXIL translation logic itself. The
attached DXBC container is well-formed (confirmed below), so the reported error is very
plausibly unrelated to its content.

## Source citations (ground truth `89e2f98e2`, tree-identical to `main-debug` outside the
triage skill directory)

`projects/dxilconv/tools/dxbc2dxil/dxbc2dxil.cpp`:

```
224:  // Convert DXBC to DXIL.
225:  CComPtr<IDxbcConverter> converter;
226:  IFT(CreateDxbcConverter(&converter));
227:
228:  void *pDxilPtr;
229:  UINT32 DxilSize;
230:  IFT(converter->Convert(pDxbcPtr, DxbcSize, ...));
```

```
326:HRESULT Converter::CreateDxbcConverter(IDxbcConverter **ppConverter) {
327:  if (m_pfnDxilConv_DxcCreateInstance == nullptr) {
328:    IFR(GetDxcCreateInstance(L"dxilconv.dll",
329:                             &m_pfnDxilConv_DxcCreateInstance));
330:  }
...
```

```
337:HRESULT Converter::GetDxcCreateInstance(LPCWSTR dllFileName,
338:                                        DxcCreateInstanceProc *ppFn) {
339:  HMODULE hModule =
340:      LoadLibraryExW(dllFileName, NULL, LOAD_LIBRARY_SEARCH_APPLICATION_DIR);
341:  if (hModule == NULL) {
342:    return HRESULT_FROM_WIN32(GetLastError());
343:  }
344:
345:  FARPROC pFn = GetProcAddress(hModule, "DxcCreateInstance");
346:  if (pFn == NULL) {
347:    return HRESULT_FROM_WIN32(GetLastError());
348:  }
```

```
368:      if (pMsg == nullptr || *pMsg == '\0') {
369:        sprintf_s(printBuffer, _countof(printBuffer),
370:                  "Conversion failed - error code 0x%08x.", E.hr);
```

`LoadLibraryExW`/`GetProcAddress` are the **only** two dynamic-load calls anywhere in
`projects/dxilconv` (confirmed with a project-wide search); `GetDxcCreateInstance` is shared by
both the `/disasm-dxbc` path (loads `dxcompiler.dll`) and the plain conversion path (loads
`dxilconv.dll`). A `GetProcAddress` failure would report `ERROR_PROC_NOT_FOUND` (127, HRESULT
`0x8007007f`), one past the reporter's code -- so `0x8007007e` specifically means
`LoadLibraryExW` itself failed to find the module, not merely a missing export in an otherwise
loadable DLL. The reporter did not use `/disasm-dxbc` (their comment describes a plain
conversion attempt), so the load target is `dxilconv.dll`.

## HRESULT arithmetic, confirmed both by calculation and by a standalone harness

`HRESULT_FROM_WIN32(x) = (x & 0xFFFF) | (FACILITY_WIN32 << 16) | 0x80000000`, `FACILITY_WIN32 =
7`. For `x = ERROR_MOD_NOT_FOUND = 126 = 0x7E`: `0x7E | 0x70000 | 0x80000000 = 0x8007007E` --
exactly the reporter's quoted code.

This is also reproduced directly (not just by hand arithmetic) with a small standalone harness
(`manual-case-loadlibrary-harness.cpp`), compiled with `cl.exe` via `vcvarsall.bat` entirely
outside the CMake build tree (no DXC target touched, same pattern as #4786's ABI harness) --
see `manual-case-loadlibrary-gen.py`/`manual-case-loadlibrary.txt` for the exact commands and
full output:

```
LoadLibraryExW("missing", LOAD_LIBRARY_SEARCH_APPLICATION_DIR):
  hModule = 0000000000000000
  GetLastError() = 126 (0x0000007E)
  HRESULT_FROM_WIN32(GetLastError()) = 0x8007007E
  matches issue's reported 0x8007007e: YES

Control: LoadLibraryExW("kernel32.dll", SEARCH_SYSTEM32):
  hModule = 00007FFE3EC90000 (loaded OK)

Control: HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND=2) = 0x80070002 (distinct from module-not-found)
```

The first control proves the harness's failure path is not simply "every load fails here"; the
second proves a missing *input file* (which would be reported by
`hlsl::ReadBinaryFile`'s own `IFT(...)` earlier in `Run()`, before `CreateDxbcConverter` is even
reached) would print a numerically distinct code, so the two failure modes cannot be confused.

## Why this checkout cannot execute the actual conversion

`dxbc2dxil.exe` and `dxilconv.dll` do not exist anywhere under `build/`
(`Get-ChildItem -Recurse -Include dxbc2dxil.exe,dxilconv.dll` returns nothing), and
`build/CMakeCache.txt` has `HLSL_BUILD_DXILCONV:BOOL=OFF` -- the same configuration #4786 found.
Enabling it would mean reconfiguring the shared CMake cache and building new targets in the
shared `build/` tree, which this session's boundary prohibits (no rebuilds). No catalogued
stable release ships these binaries either (per #4786, not independently re-derived here).
So neither the module-load claim nor the conversion-logic claim can be executed end to end in
this environment, under any configuration -- not merely the one currently configured.

## Is the module-load failure a build-system defect, or a build/deployment condition?

Checked whether a normal, default build of this repository would leave `dxbc2dxil.exe` without
its `dxilconv.dll` next to it:

- `HLSL_BUILD_DXILCONV` defaults to **`ON`** (`CMakeLists.txt:85`), so both
  `projects/dxilconv/tools/dxbc2dxil` and `projects/dxilconv/tools/dxilconv` are configured by
  default.
- `dxbc2dxil` (executable, via `add_dxilconv_project_executable` ->
  `add_llvm_executable`) and `dxilconv` (shared library, via `add_dxilconv_project_library`
  `dxilconv SHARED` -> `add_llvm_library`) both place their output in the same
  `LLVM_RUNTIME_OUTPUT_INTDIR` (the common `bin/` directory every DXC tool and DLL shares),
  confirmed from `projects/dxilconv/CMakeLists.txt`'s macros and
  `cmake/modules/AddLLVM.cmake`'s `set_output_directory` call inside `add_llvm_executable`
  (line 656).
- Neither target is `EXCLUDE_FROM_ALL`: that property is only set by `add_llvm_tool` (when
  `LLVM_BUILD_TOOLS` is off) or `add_llvm_example`, neither of which `dxilconv`/`dxbc2dxil` use
  -- they call `add_llvm_executable`/`add_llvm_library` directly, whose own `EXCLUDE_FROM_ALL`
  defaults to `OFF` (`AddLLVM.cmake:655`). So a default build of the `ALL_BUILD`/`all` target
  (what `cmake --build .` does with no `--target` specified) builds both, side by side, and the
  tool should work.
- `dxbc2dxil`'s `CMakeLists.txt` declares `add_dependencies(dxbc2dxil DxbcConverter)` only --
  **not** `dxilconv`. `DxbcConverter` is a separate static library that `dxbc2dxil` links
  directly (`target_link_libraries(dxbc2dxil PRIVATE DxbcConverter ...)`), while `dxilconv.dll`
  is loaded purely at runtime via `LoadLibraryExW`; there is no CMake dependency edge from
  `dxbc2dxil` to `dxilconv` at all. This means **building the `dxbc2dxil` target alone** (e.g.
  `cmake --build . --target dxbc2dxil`, or an IDE building only that one project) does not
  force `dxilconv.dll` to be built or copied anywhere, and would reproduce exactly the
  reporter's symptom on a machine where `dxbc2dxil.exe` was later run without ever having built
  or retained `dxilconv.dll`.

This is a plausible, source-grounded explanation for a report with no further detail: the
reporter's own words -- "I compiled the src of this project last week which i think included
the fxc compiler if i am not mistaken" -- read as genuine uncertainty about exactly what was
built, consistent with a partial/selective build or a copied `dxbc2dxil.exe` missing its
sibling `dxilconv.dll`, rather than with a full default build. This cannot be proven from here
(the reporter's own build log/directory listing is not available), and it is not established
that this is a build-system defect worth fixing (a full build works fine) rather than a
between-executable-and-DLL a user can trip on if they copy files selectively -- both readings
are consistent with everything on record.

## Attachment: the DXBC container is well-formed

`attachment-0.txt` (724 bytes, downloaded from the issue's public GitHub attachment URL) opens
with the `DXBC` fourcc (`44 58 42 43`) and its `TotalSize` field (offset 24, little-endian
`D4 02 00 00` = `0x2D4` = 724) matches the file's exact length, with a `ChunkCount` of 6 --
consistent with an ordinary FXC-compiled shader container (e.g. `RDEF`/`ISGN`/`OSGN`/`SHEX`/
`STAT` plus one more chunk), not truncated or corrupted data. This does not prove the shader
would convert cleanly (claim 2 in `expected.md` is unmeasurable here regardless), but it rules
out "the attachment itself is garbage" as an alternative explanation for the reported failure,
and is consistent with the module-load explanation being unrelated to the DXBC's own content.

## What this does and does not establish

- **Established, high confidence (source-verifiable, corroborated by a standalone harness):**
  `0x8007007e` is `HRESULT_FROM_WIN32(ERROR_MOD_NOT_FOUND)`; the only place in
  `dxbc2dxil.cpp`/`DxbcConverter` that can produce this exact HRESULT is
  `GetDxcCreateInstance`'s `LoadLibraryExW` call for `dxilconv.dll`, which runs before any DXBC
  content is examined; this call site and shape are unchanged at ground truth. A normal default
  (`ALL_BUILD`) build of this repository builds both `dxbc2dxil.exe` and `dxilconv.dll` into the
  same output directory, but `dxbc2dxil` declares no build dependency on `dxilconv`, so building
  or deploying the two selectively can separate them.
- **Not established, and out of reach in this environment under any configuration:** whether
  the reporter's attached DXBC would convert correctly once the converter module *is* loaded --
  this checkout does not build `dxilconv` (`HLSL_BUILD_DXILCONV=OFF`, no rebuilds permitted),
  and no catalogued release ships these binaries either. Whether the reporter specifically hit
  a partial build or a selective copy (as opposed to some other, unconsidered cause of the same
  HRESULT) is also not established -- no further detail was ever requested or provided after
  the DXBC was attached in 2023.
- **Text staleness:** none. The issue body and both comments remain accurate as a description
  of what the reporter observed; nothing in the thread claims a fix, and the maintainer's only
  comment (asking for more information) still accurately describes the state of available
  evidence even after the DXBC was attached, since a DXBC alone cannot settle which of the two
  claims above is the real cause.

## Compiler Explorer

Skipped. `dxbc2dxil` is never invoked by any CE `dxc` pane (CE compiles HLSL through the same
front end as local `dxc.exe`, which never reaches `DxbcConverter`/`dxilconv.dll` at all -- same
reasoning as #4786), and there is no HLSL source to compile even if a pane existed for it. A CE
link would show nothing relevant and risks being misread as evidence about this issue. See
`verdict.json` (`godbolt_skip`).

## Labels

Current: `bug`, `dxilconv`. Neither removal is warranted -- `dxilconv` is accurate regardless
of which explanation is right, and a real conversion failure being reported is fairly labelled
`bug` even though the most likely cause here is a build/deployment condition rather than a
`DxbcConverter` logic defect. Proposed addition: `needs repro steps` ("Cannot reproduce or
don't have repro informations") -- the missing piece of information that would actually settle
this (whether `dxilconv.dll` was present next to the reporter's `dxbc2dxil.exe`, and/or a full
rebuild-and-retry) was never requested after the DXBC was attached, and no maintainer
established which of the two explanations in `expected.md` applies.
