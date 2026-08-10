> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3276](https://github.com/microsoft/DirectXShaderCompiler/issues/3276).

Still accurate on `main` (`13730886e`): the default `install` target installs the LLVM and
Clang headers, static archives and developer tools. Two things have changed since 2020 that
aren't recorded here, and both are undocumented.

**1. `install-distribution` does what you asked for.** [#5154](https://github.com/microsoft/DirectXShaderCompiler/pull/5154)
(`4f5e4d1b7`, in releases since v1.7.2308) added a distribution target whose components
default to `dxc;dxcompiler;dxc-headers` ([`CMakeLists.txt:807-825`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/CMakeLists.txt#L807-L825)).
Installing those three components deposits six files — the `dxc` executable, `dxcompiler`, and
`config.h` / `dxcapi.h` / `dxcerrors.h` / `dxcisense.h` under `<prefix>/include/dxc`. DXC's own
Linux artifact is built this way: `ninja -C build install-distribution`
([`gcp-pipelines/x86_64-linux-clang.yml:36-44`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/gcp-pipelines/x86_64-linux-clang.yml#L36-L44)).

**2. `-DLLVM_INSTALL_TOOLCHAIN_ONLY=ON` already removes most of the bloat**, if you want a
normal `install` rather than a distribution one. Configuring twice with only that variable
changed:

| under `<prefix>` | default | `TOOLCHAIN_ONLY=ON` |
| --- | --- | --- |
| `lib/LLVM*` archives | 34 | 0 |
| `lib/clang*` archives | 20 | 1 (`libclang`) |
| `bin/` LLVM developer tools | 11 | 0 |
| `include/` header trees | `llvm`, `llvm-c`, `clang`, `clang-c` | `clang-c` |
| `share/llvm/cmake` | 9 files | absent |

It is not a complete answer. `include/clang-c` survives because
[`tools/clang/CMakeLists.txt:426`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/tools/clang/CMakeLists.txt#L426)
installs it a second time *outside* the `if (NOT LLVM_INSTALL_TOOLCHAIN_ONLY)` block that ends
at line 424; the vendored SPIRV-Tools archives, CMake packages and `lib/pkgconfig` aren't
governed by the LLVM option; and `bin/` still gets `dxa`, `dxl`, `dxopt`, `dxr`, `dxv` and the
test binaries.

The `include/dxc` complaint in the second comment no longer applies to the install tree:
`include/dxc` is now an explicit four-file `install(FILES ...)` list, so `CMakeLists.txt` and
`d3dx12.h` don't reach it.

Neither `install-distribution` nor the option combination appears in any README, build script
or docs page — a grep finds `install-distribution` only in `CMakeLists.txt` itself and that one
CI file. So the practical remainder of this issue may be documentation plus the four gaps
above, rather than the original request.

Measured on Windows with the Visual Studio generator, using DXC's own
`cmake/caches/PredefinedParams.cmake` (the \*nix option set) on both sides of the comparison.
The install rules involved carry no `if(WIN32)`/`if(UNIX)` guard, so the finding should
transfer, but the exact file list on Linux will differ — no Linux build was configured.

Label suggestion: add `build` (this is entirely CMake install rules) and `up-for-grabs`
(matching the 2024-07-09 comment inviting a PR); `linux` may also be inapt, since the rules are not platform-guarded and the same bloat appears on Windows. I measured this only on Windows, though, so I would defer to maintainer judgement on whether that label records a user-facing workflow distinction not visible in the rules.

---
<sub>Triaged with AI assistance. This is a build-system issue, so no compiler output was
produced; the evidence is CMake's own generated install rules, read from two freshly
configured build trees. Please flag anything that looks wrong.</sub>
