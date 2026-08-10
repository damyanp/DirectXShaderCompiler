# Expected symptom — #3276 "Install target installs lots of unnecessary LLVM outputs"

*Written before any investigation, from the issue text alone (step 2 of the skill).*

Reporter: `expipiplus1`, 2020-11-20. Label: `linux`.

## What the issue claims

1. Running `make install` / `ninja install` on a DXC build "installs heaps of clang and llvm
   build products".
2. The reporter's expectation: **only** the `dxc` executable, the dxc headers and the dxc
   libraries should be installed — "i.e. what is copied here", pointing at the (then-current)
   `appveyor.yml` artifact list.
3. Evidence supplied: a gist listing the full set of installed files.
4. Follow-up comment (same reporter, 2020-11-21): the installed `include/dxc` directory
   itself carries non-dxc content — `CMakeLists.txt` files and `d3dx12.h`.
5. Maintainer comment (`damyanp`, 2024-07-09): Microsoft will not spend time on this, but a
   PR would be considered. So as of mid-2024 the maintainers treated it as unfixed.

## What "this reproduces" means

The default install target of a stock DXC configure+build deposits, under the install prefix,
a large set of files that are **LLVM/Clang build products rather than DXC deliverables**.
Concretely, the symptom is present if any of the following hold for a default configuration
(no extra `-D` options beyond what the DXC preset requires):

* **S1 — LLVM/Clang static libraries are installed.** `<prefix>/lib/` contains `libLLVM*.a` /
  `LLVM*.lib`, `libclang*.a` / `clang*.lib` and similar, i.e. dozens-to-hundreds of archives
  that no consumer of `dxc`/`dxcompiler` links against.
* **S2 — LLVM/Clang headers are installed.** `<prefix>/include/llvm/`, `include/llvm-c/`,
  `include/clang/`, `include/clang-c/` are populated.
* **S3 — Non-DXC tools are installed.** `<prefix>/bin/` contains LLVM/Clang developer tools
  (`llvm-as`, `opt`, `llc`, `clang-format`, `FileCheck`, …) beyond `dxc`/`dxa`/`dxr`/`dxv`
  and the `dxcompiler` shared library.
* **S4 — `include/dxc` carries non-header content.** The installed `include/dxc` tree contains
  `CMakeLists.txt` (build-system files) or headers not owned by DXC's public surface, with
  `d3dx12.h` named explicitly by the reporter.
* **S5 — No supported way to get only the DXC deliverables.** There is no documented
  option/component (e.g. `LLVM_INSTALL_TOOLCHAIN_ONLY`, a `--component` name, or a DXC-specific
  cache variable) that a consumer can set to install just `dxc` + the DXC headers + the DXC
  libraries.

`repros` = the install set still contains LLVM/Clang build products by default (S1–S4 largely
hold) **and** S5 holds, i.e. there is still no trimmed install path.

`does-not-repro` / fixed = the default install has been trimmed to DXC deliverables, **or** a
supported option now exists to produce that trimmed set (in which case S5 fails and the issue's
actionable core is answered even if the default is unchanged).

`changed-behavior` = the install set is materially different from the 2020 gist but still
carries substantial LLVM/Clang content — e.g. libraries dropped but headers retained.

## Why the compiler is the wrong instrument

There is **no shader repro here and no `dxc` invocation can answer the question.** The claim
is about what CMake's `install` target deposits on disk. A clean compile of any HLSL source is
entirely compatible with the report being true, so per the skill's step-5 guidance the expected
status is **`not-compiler-verifiable`**: the evidence must be the generated install rules /
install manifest and the `install()` calls in the CMake sources, not compiler output.

Repro quality (recorded before investigating): **partial** — the reporter gives the exact
commands (`make install` / `ninja install`) and a full file listing, but no configure line, no
CMake options, no toolchain, and the gist may not survive. The build configuration is the
missing half, and install rules can be configuration- and platform-dependent.

## Known limitations to state up front

* The label is `linux` and the reporter used `make`/`ninja`; **this triage machine is Windows.**
  Install rules can be guarded by `if(WIN32)` / `if(UNIX)`, so any Windows-side measurement must
  be checked against those guards before it is generalised to the reporter's platform.
* If a full configure is unavailable or too expensive, the fallback is static analysis of the
  `install()` rules, clearly labelled as such.

## What would make this `close-fixed`

Either the default install set is now DXC-only, or an option now exists (and is discoverable)
that produces the trimmed set the reporter asked for. Anything less — e.g. the install set is
merely smaller — is `repros` or `changed-behavior`, not fixed.
