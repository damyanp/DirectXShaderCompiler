# Notes — #5985 "DllMain calls LoadLibrary for dxil.dll, could cause deadlock or crash"

## Ground truth

`main-debug` compiler, git commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (as recorded in
`.cache/compilers/main-debug.json`; self-reported `dxc --version` shows a local build hash
`7665270b9` for the same reason documented project-wide — the local build's own commit is a
fork-local snapshot, not the upstream identity; the tree is what's cited).

This issue is architectural/source-level, not a compile-time symptom: nothing a `dxc`
invocation can observe distinguishes "DllMain calls LoadLibrary under the loader lock" from
"it doesn't" — the hazard is about *when* code executes relative to the OS loader lock, not
what a shader compiles to. No `cmd.txt`/`match.json`/Compiler Explorer link were produced for
this issue (`godbolt --skip` recorded); per the skill's guidance for issues the compiler's
output cannot answer, this was checked by reading the current source and the already-built
ground-truth binary instead of manufacturing a hollow predicate.

## What the issue claims

Quoting the issue body and its embedded callstack, filed 2023-11-07:

```
dxcompiler.dll!dxc::DxcDllSupport::InitializeInternal(...)     Line 34
dxcompiler.dll!dxc::DxcDllSupport::InitializeForDll(...)       Line 95
dxcompiler.dll!DxilLibInitialize()                             Line 29
dxcompiler.dll!InitMaybeFail()                                 Line 68
dxcompiler.dll!DllMain(...)                                     Line 104
```

i.e. `dxcompiler.dll`'s `DllMain` → `InitMaybeFail()` → `DxilLibInitialize()` →
`DxcDllSupport::InitializeForDll` → `InitializeInternal`, which calls `LoadLibraryA("dxil.dll")`
(`include/dxc/Support/dxcapi.use.h`, quoted line 34 in the issue). Per Microsoft's DLL
best-practices guidance the issue quotes, calling `LoadLibrary`/`LoadLibraryEx` — directly or
indirectly — from `DllMain` can deadlock or crash a process, because `DllMain` runs under the
loader lock.

## Current source (ground truth)

`tools/clang/tools/dxcompiler/DXCompiler.cpp`'s `InitMaybeFail()` (called from `DllMain` on
`DLL_PROCESS_ATTACH`) today reads:

```cpp
IFC(hlsl::SetupRegistryPassForHLSL());
IFC(hlsl::SetupRegistryPassForPIX());
if (hlsl::options::initHlslOptTable()) { ... }
```

There is **no call to `DxilLibInitialize()`**, and the file no longer even includes
`dxillib.h`. `DLL_PROCESS_DETACH` likewise no longer calls `DxilLibCleanup(...)`. Confirmed by
`grep`/`Select-String` across every `.cpp`/`.h` under `tools/clang/tools/dxcompiler/`: no
reference to `DxilLibInitialize`, `LoadLibrary`, or `dxil.dll` remains reachable from
`dxcompiler.dll`'s init/shutdown path.

The reason: `dxcutil.cpp`'s validation call sites (`RunValidation`,
`ValidateRootSignatureInContainer`, `GetValidatorVersion`) now call `CreateDxcValidator(...)`,
described in-source as "the locally-linked validator" — i.e. the validator is statically linked
into `dxcompiler.dll` itself. There is no longer any runtime dependency on a separate
`dxil.dll` for `dxcompiler.dll`'s own validation path, so nothing in this DLL needs to
`LoadLibrary` it at all, from `DllMain` or anywhere else. (`dumpbin /dependents` on the
ground-truth `build/Debug/bin/dxcompiler.dll` shows no `dxil.dll`-related dependency, though
that check alone is not conclusive — a `LoadLibrary` call would not show up as a static import
either way; the source read is what settles it.)

## Fixing commit

`git log`/GitHub commit history for `tools/clang/tools/dxcompiler/DXCompiler.cpp` (queried via
`gh api repos/microsoft/DirectXShaderCompiler/commits?path=...`, since the local clone here is
shallow — only 207 commits — and does not contain this file's older history) shows the
`IFC(DxilLibInitialize())` call and the `DxilLibCleanup` calls were removed in:

```
77b2ff676  2025-06-05  NFC: remove dead external validation code paths from dxcompiler (#7451)
```

Commit message: "DXC has now been changed to use the internal validator (loaded by
dxcompiler.dll) by default. This PR removes the ability for dxc.exe to load dxil.dll in
preparation for a series of changes to fix external validation handling." The diff (fetched via
`gh api repos/.../commits/77b2ff676`) removes exactly the three things: the `#include
"dxillib.h"`, the `IFC(DxilLibInitialize());` line, and the `DxilLibCleanup(...)` calls on
`DLL_PROCESS_DETACH`.

**Ancestry check, and a discriminating control that mattered:** `git merge-base --is-ancestor
77b2ff676 89e2f98e29c289ae8ad9e00dd310104fea9fd7df` returned exit 1 (not an ancestor) even
though both SHAs resolve locally as commit objects (`git cat-file -t` succeeds for both). This
looked like a real negative, but the local clone is shallow (`git rev-parse
--is-shallow-repository` → true, only 207 commits on `HEAD`'s branch), which truncates ancestry
chains at the shallow boundary and can make a genuine ancestor read as absent — the same class
of trap as the "a negative from a command that errored is not a negative" note for missing
refs. Checked instead against the authoritative remote:

```
gh api "repos/microsoft/DirectXShaderCompiler/compare/77b2ff676...89e2f98e29c289ae8ad9e00dd310104fea9fd7df"
  -> {"ahead_by": 479, "behind_by": 0, "status": "ahead"}
```

`behind_by: 0` means the merge-base of the two commits is `77b2ff676` itself, i.e. it **is**
an ancestor of ground truth (479 commits behind `main` at the ground-truth commit). The fix
predates ground truth by well over a year.

## What is NOT fixed

- **`tools/clang/tools/dxrfallbackcompiler/DXCompiler.cpp`** — the DXR fallback-layer DLL —
  still has the *identical* pattern today: `InitMaybeFail()` calls `IFC(DxilLibInitialize())`,
  and `DLL_PROCESS_DETACH` still calls `DxilLibCleanup(DxilLibCleanUpType::UnloadLibrary /
  ProcessTermination)`. This is a separate, much less commonly embedded binary (a legacy DX12
  raytracing fallback layer, not what Chrome or the other commenters here are loading), and the
  issue never names it directly, but it is the same defect, unfixed, in a sibling DLL that
  ships from this repo.
- **`projects/dxilconv`** (the DXBC→DXIL converter the issue also names) does not exhibit this
  pattern in the current tree — the only `LoadLibrary` call found under
  `projects/dxilconv/` is an ordinary application-level call in the `dxbc2dxil.exe`
  command-line tool (`Converter::GetDxcCreateInstance`), not inside any `DllMain`, so it is not
  subject to the loader-lock hazard described here. Checking `dxilconv.cpp`'s content at its
  earliest commit in this repo (`a42ffbf49`, 2020-02-11, via `gh api .../contents/...?ref=...`)
  shows no `DxilLibInitialize`/`LoadLibrary`/`dxil.dll` reference there either, so it is unclear
  this specific file/project ever had the problem the issue attributes to it; not asserting a
  fix for a claim that could not be confirmed to begin with.
- **amaiorano's proposed architecture change** (moving *all* of `DllMain`'s work to
  `DxcCreateInstance*`) was not done wholesale: `InitMaybeFail()` still runs
  `SetupRegistryPassForHLSL`/`SetupRegistryPassForPIX`/`initHlslOptTable` from `DllMain`.
  These don't call `LoadLibrary`, so they aren't the specific hazard named in the title, but
  the broader `tech-debt` ask is only partially addressed.
- **manvis's ask** (an explicit API to hand `DxcCreateInstance` a pre-loaded/pathed `dxil.dll`)
  and **damyanp's question** (statically linking `dxil.dll`'s code into `dxcompiler.dll`
  entirely) are both still open; the fix took a different, narrower route — removing
  `dxcompiler.dll`'s *own* runtime dependency on external `dxil.dll` validation rather than
  exposing a path-selection API or eliminating the separate `dxil.dll` binary altogether.

## Assessment

The exact defect reported — `dxcompiler.dll`'s `DllMain` calling `LoadLibrary` (via
`DxilLibInitialize`) for `dxil.dll` while holding the loader lock — is fixed as of ground
truth, via commit 77b2ff676 (PR #7451, merged 2025-06-05, ~14 months before ground truth).
`dxcompiler.dll` is the binary the issue's own callstack names and the one the reporter (and
Chrome) actually embeds; `dxc.exe`'s in-process use of `dxcompiler.dll` is likewise unaffected.
A sibling binary (`dxrfallbackcompiler.dll`) still has the identical unfixed pattern, but it is
outside what this issue reports or what its discussion ever named.
