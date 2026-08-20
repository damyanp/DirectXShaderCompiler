> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6016](https://github.com/microsoft/DirectXShaderCompiler/issues/6016).

Still reproduces on `main` (Debug build at commit `89e2f98e2`, 2026-08):

```
error: Failed to allocate all input signature elements in available space.
UNREACHABLE executed at lib\HLSL\HLSignatureLower.cpp:523!
```

Bisecting the released binaries, this regressed between v1.7.2207 (last good) and v1.7.2212
(first bad). Through v1.7.2207 the same detected condition was an ordinary diagnosed error:

```
repro.hlsl:19:1: error: Failed to allocate all input signature elements in available space.
repro.hlsl:19:1: error: Failed to allocate all output signature elements in available space.
```

That matches @tex3d's diagnosis in this thread exactly: `21e56159e` ("Add diagnostic
tests (#4599)") is inside the v1.7.2207..v1.7.2212 window and is the only commit in that
window touching `HLSignatureLower.cpp`, so it is confirmed as the regressing change, not just
plausible. `main`'s `AllocateDxilInputOutputs()` still routes both the input- and
output-signature allocation-failure checks to `llvm_unreachable` (`HLSignatureLower.cpp:521-531`),
so the fix described in the thread — restoring these to diagnosed errors — has not landed.

Compiler Explorer: https://godbolt.org/z/h7YxEKKT5 (CE's oldest DXC, 1.6.2112, still gives the
clean diagnostic; `dxc_trunk` crashes the process outright — SIGSEGV rather than the
reporter's SIGABRT, since CE's build has asserts compiled out, but a crash either way).

Per this thread, no shader-model change is being requested — everyone agrees this much
packed IO is a legitimate limit. Suggest keeping this open and labeled as-is
(`bug`, `crash`, `diagnostic`, `incorrect-code` all still fit); the remaining work is turning
the `llvm_unreachable` back into the diagnostic it used to be.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
