> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5985](https://github.com/microsoft/DirectXShaderCompiler/issues/5985).

The specific hazard reported here — `dxcompiler.dll`'s `DllMain` calling `LoadLibrary`
(via `DxilLibInitialize`) to load `dxil.dll` while holding the loader lock — is fixed on
`main` (checked at `89e2f98e2`, 2026-08-12).

`InitMaybeFail()` in `tools/clang/tools/dxcompiler/DXCompiler.cpp`, called from `DllMain` on
`DLL_PROCESS_ATTACH`, no longer calls `DxilLibInitialize()` at all, and the file no longer
includes `dxillib.h`. `DLL_PROCESS_DETACH` no longer calls `DxilLibCleanup`. `dxcompiler.dll`'s
validation now goes through a statically-linked, in-process validator
(`CreateDxcValidator` in `dxcutil.cpp`, "the locally-linked validator"), so there is no longer
any runtime dependency on loading `dxil.dll` from this DLL, from `DllMain` or otherwise.

Removed by commit `77b2ff676` ("NFC: remove dead external validation code paths from
dxcompiler", [PR #7451](https://github.com/microsoft/DirectXShaderCompiler/pull/7451), merged
2025-06-05): "DXC has now been changed to use the internal validator (loaded by
dxcompiler.dll) by default. This PR removes the ability for dxc.exe to load dxil.dll in
preparation for a series of changes to fix external validation handling." That commit is
confirmed to be 479 commits behind `main` at the checked commit (`gh api .../compare/...`),
so the fix predates this check by well over a year.

Two things from this thread remain open, for what it's worth:

- `tools/clang/tools/dxrfallbackcompiler/DXCompiler.cpp` (the DXR fallback-layer DLL) still has
  the identical pattern — `DllMain` still calls `DxilLibInitialize()`/`LoadLibrary` for
  `dxil.dll`. It's a much less commonly embedded binary than `dxcompiler.dll`, and this issue
  never named it, but it's the same defect in a sibling DLL.
- The broader ask to move the rest of `DllMain`'s work to `DxcCreateInstance*`, and the request
  for an explicit API to hand in a pre-loaded/pathed `dxil.dll`, are both still open — the fix
  took the narrower route of removing `dxcompiler.dll`'s own dependency on external `dxil.dll`
  validation rather than restructuring initialization more broadly.

Suggest: `crash` no longer applies to `dxcompiler.dll` specifically; `tech-debt` still fits
given the remaining `dxrfallbackcompiler.dll` instance and the unaddressed API asks in this
thread.

---
<sub>Triaged with AI assistance. This is a source/architecture issue, not a compile-time one,
so no compiler output was produced; the evidence is the current `DllMain` source, the fixing
commit's diff, and its ancestry relative to the checked commit. Please flag anything that
looks wrong.</sub>
