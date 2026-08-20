> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5079](https://github.com/microsoft/DirectXShaderCompiler/issues/5079).

Still reproduces on `main` (main-debug @ `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).

This is a genuine header conflict, not something specific to your build: DXC's own
non-Windows shim (`include/dxc/WinAdapter.h`, pulled in by `dxc/dxcapi.h` whenever
`_WIN32` is undefined) and DirectX-Headers' own non-Windows shim
(`wsl/winadapter.h`/`wsl/stubs/basetsd.h`) each independently define the same set of
Windows base types, with different underlying types for several of them. Reproduced
locally with this repository's own vendored copies of both header trees — DXC's
`include/dxc/WinAdapter.h` and the pinned DirectX-Headers submodule's
`wsl/winadapter.h` (the pre-split, single-file predecessor of the `wsl/stubs/*.h`
form your build hits; same content, per the investigation in #8431 below) —
compiled with `clang -U_WIN32` (no dxc.exe angle applies; this is a C++ preprocessor
question, not a shader-compilation one):

```
include/dxc/WinAdapter.h:303:14: error: typedef redefinition with different types ('BYTE' (aka 'unsigned char') vs 'char')
include/dxc/WinAdapter.h:306:14: error: typedef redefinition with different types ('bool' vs 'uint32_t' (aka 'unsigned int'))
include/dxc/WinAdapter.h:310:14: error: typedef redefinition with different types ('long' vs 'int32_t' (aka 'int'))
include/dxc/WinAdapter.h:312:23: error: typedef redefinition with different types ('unsigned long' vs 'uint32_t' (aka 'unsigned int'))
include/dxc/WinAdapter.h:376:16: error: redefinition of '_GUID'
```

(paths shown relative to the repo; full capture in `manual-case-clang-conflict.txt`).

**Nothing has changed since this was filed.** The DirectX-Headers submodule pin
(`980971e835876dc0cde415e8f9bc646e64667bf7`) has not moved since it was first added to
this repository in 2022-11-23 (PR #4810) — before this issue was even filed.

A fix already exists: PR #8431 ("Update DirectX-Headers to latest", opened
2026-05-08) bumps the submodule and removes the now-duplicated types from
`WinAdapter.h`. It's open and mergeable, but discussion has stalled since
2026-05-11 on two unresolved design questions its own author raised: `BOOL`'s
underlying type changing from `bool` to `uint32_t` (an ABI-visible change for a
public type), and whether users of the released `dxc/dxcapi.h`/`WinAdapter.h` as a
standalone installed header would now need DirectX-Headers on their own include
path too. Both need a maintainer decision, not another investigation — the repro
and root cause are already well understood.

Suggest keeping the `build` label and adding `linux`: the conflict is entirely in
the non-Windows (`_WIN32`-undefined) code path of both shims.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
