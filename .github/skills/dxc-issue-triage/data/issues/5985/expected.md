# Expected symptom (#5985)

"This reproduces" means: `dxcompiler.dll`'s `DllMain` (running under the OS loader lock, on
`DLL_PROCESS_ATTACH`) calls `LoadLibrary`/`LoadLibraryA`/`LoadLibraryEx`, directly or
indirectly, to load `dxil.dll`. Per Microsoft's DLL best-practices guidance quoted in the
issue, that is one of the specific operations DllMain must never perform, because it can
deadlock or crash the process (the reporter's own callstack shows exactly this call chain:
`DllMain -> InitMaybeFail -> DxilLibInitialize -> DxcDllSupport::InitializeForDll ->
InitializeInternal -> LoadLibraryA("dxil.dll")`, quoting
`include/dxc/Support/dxcapi.use.h` line 34 as filed).

This is not a compile-time symptom: no `dxc` invocation demonstrates a loader-lock deadlock or
its absence (the hazard is about *when* code runs relative to the loader lock, not what a
shader compiles to). The only way to check it is to read the current DllMain implementation(s)
that ship `dxcompiler`-family binaries and see whether any of them still calls into DXIL
library loading from `DllMain`/a static-init path executed while the loader lock is held.

"Does not reproduce" means: no shipped `DllMain` for the compiler DLL the issue is about
(`dxcompiler.dll`) calls `LoadLibrary` for `dxil.dll` (or anything else) during
`DLL_PROCESS_ATTACH`/`DLL_PROCESS_DETACH`.

Repro quality: **complete** — the issue names the exact source line, quotes the exact call
stack, and even names the commit (`5a916c56d`) that introduced the behavior, so the claim is
unambiguous and directly checkable against source.

No `cmd.txt`/`match.json`/godbolt link are produced for this issue; per the skill's guidance
for issues the compiler's compile-time output cannot answer, the check is done by reading the
source and the built binary rather than by manufacturing a hollow predicate.
