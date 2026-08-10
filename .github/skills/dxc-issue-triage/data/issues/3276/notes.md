# #3276 — Install target installs lots of unnecessary LLVM outputs

**Status: `not-compiler-verifiable`.** This is a build-system issue. No `dxc`
invocation can answer it, so there is no `repro.hlsl`, no `cmd.txt` and no
`match.json` — see "Why there is no predicate" below. The evidence is the
CMake `install()` rules plus a real, measured install into a scratch prefix.

Ground truth: `main-debug`, Debug build, self-reporting
`1.9.0.5433 (triage, ab5400907)`. That merge is fork-local; the compiler source
is identical to upstream **`13730886e`** (`git diff --name-only HEAD 13730886e`
returns 0 files outside the triage skill directory; control against an older
commit returns 3733, so the query can detect differences).

## What was measured

The build tree used for the measurements is the same configured tree the
ground-truth compiler was built from: Visual Studio generator, x64,
`LLVM_INSTALL_TOOLCHAIN_ONLY=OFF` (the default),
`LLVM_DISTRIBUTION_COMPONENTS=dxc;dxcompiler;dxc-headers` (the default),
`HLSL_INCLUDE_TESTS=ON`, `ENABLE_SPIRV_CODEGEN=ON`.

Three captures, each produced by a committed script that echoes every command
it runs:

| capture | what it is |
| --- | --- |
| `manual-case-install-rules.txt` | every install rule the configured tree would execute, parsed out of the 164 generated `cmake_install.cmake` scripts (`enumerate-install-rules.py`) |
| `manual-case-install-default.txt` | a real `cmake --install` with no `--component`, into a scratch prefix outside the repository (`measure-install.py`) |
| `manual-case-install-distribution.txt` | the same, restricted to `dxc`, `dxcompiler`, `dxc-headers` |
| `manual-case-install-headers.txt` | the same, restricted to `llvm-headers` and `Unspecified` |
| `manual-case-install-static.txt` | the `install()` rules in source, with file:line, and the git history around them (`collect-static-evidence.py`) |

Plus a **controlled A/B**: two further trees were *configured only* (never
built, never installed) into a scratch directory outside the repository, using
DXC's own `cmake/caches/PredefinedParams.cmake` — the file whose header says it
"contains the basic options required for building DXC using CMake on *nix
platforms", i.e. as close to the reporter's configuration as this machine
allows — with exactly one variable changed between them:

| capture | configure |
| --- | --- |
| `manual-case-rules-knob-off.txt` | `-C cmake/caches/PredefinedParams.cmake -DLLVM_INSTALL_TOOLCHAIN_ONLY=OFF` (the default) |
| `manual-case-rules-knob-on.txt` | the same, `-DLLVM_INSTALL_TOOLCHAIN_ONLY=ON` |

`git status` was clean outside the triage directory after both configures, so
configuring does not write into the source tree.

## Finding 1 — the reported symptom is still present on the default target

The default `install` target still deposits, per
`manual-case-install-rules.txt`:

* **71 static archives** in `<prefix>/lib` — 34 named `LLVM*`, 20 `clang*`/
  `libclang`, 7 `SPIRV-Tools*`, plus DXC's own;
* **11 LLVM developer tools** in `<prefix>/bin` — `llvm-as`, `llvm-bcanalyzer`,
  `llvm-config`, `llvm-diff`, `llvm-dis`, `llvm-extract`, `llvm-link`,
  `llvm-stress`, `llvm-tblgen`, `opt`, `verify-uselistorder`;
* **6 test binaries** in `<prefix>/bin` — `ClangHLSLTests.dll`,
  `ExecHLSLTests.dll`, `HLSLErrors.exe`, `HLSLHost.exe`, `dxc_batch.exe`,
  `test_DxrFallback.exe` (this build has `HLSL_INCLUDE_TESTS=ON`);
* **1202 headers** — measured, not estimated: installing just the
  `llvm-headers` and `Unspecified` components deposited 731 files under
  `<prefix>/include/llvm`, 19 under `include/llvm-c`, 445 under
  `include/clang` and 7 under `include/clang-c`;
* CMake package files under `<prefix>/share/llvm/cmake`,
  `<prefix>/SPIRV-Tools*/cmake` and `<prefix>/lib/pkgconfig`.

The rules responsible are unchanged from the 2020 report and are guarded by a
single knob:

* `CMakeLists.txt:769-780` — `install(DIRECTORY include/llvm include/llvm-c ...)`,
  component `llvm-headers`, `if (NOT LLVM_INSTALL_TOOLCHAIN_ONLY)`
* `CMakeLists.txt:782` — the generated `llvm` headers, same guard
* `tools/clang/CMakeLists.txt:407-415` — `install(DIRECTORY include/clang
  include/clang-c ...)`, same guard. This is the rule that produced the 487
  `include/clang*` lines in the reporter's 2020 listing.
* `tools/clang/CMakeLists.txt:426` — `install(DIRECTORY include/clang-c ...)`,
  **outside** the guard, so `LLVM_INSTALL_TOOLCHAIN_ONLY=ON` does not suppress it
* `cmake/modules/AddLLVM.cmake:570-584` — `add_llvm_library()` attaches an
  `install(TARGETS ...)` to every LLVM library by default
* `cmake/modules/AddLLVM.cmake:682-687` — `add_llvm_tool()` installs every tool
  unless `LLVM_INSTALL_TOOLCHAIN_ONLY`, whose carve-out list is
  `llvm-ar;llvm-objdump` (`AddLLVM.cmake:670-673`) — **neither of which DXC
  builds** (`tools/CMakeLists.txt:31` and `:43` both comment out the
  `add_llvm_tool_subdirectory` call), so that knob is all-or-nothing for `bin/`
  here. Confirmed by measurement in Finding 2: with the knob on, zero LLVM tools
  are installed rather than a reduced set.
* `tools/clang/CMakeLists.txt:377-383` — `add_clang_library()`, same shape
* `CMakeLists.txt:70` — `option(LLVM_INSTALL_TOOLCHAIN_ONLY ... OFF)`

Only the last three years of history were checked for a change to these rules:
`git log --since=2020-11-20 -- CMakeLists.txt cmake/modules/AddLLVM.cmake
tools/clang/CMakeLists.txt` lists 46 commits and none of them trims the default
install set (see the absence check in `manual-case-install-static.txt`).

## Finding 2 — the existing knob does most, but not all, of the job (controlled A/B)

Changing exactly one variable between two otherwise identical configures:

| destination | knob **OFF** (default) | knob **ON** |
| --- | --- | --- |
| `<prefix>/lib` `LLVM*` archives | 34 | **0** |
| `<prefix>/lib` `clang*`/`libclang` archives | 20 | **1** (`libclang.lib`) |
| `<prefix>/lib` `SPIRV-Tools*` archives | 7 | 7 |
| `<prefix>/bin` LLVM developer tools | 11 | **0** |
| `<prefix>/bin` distinct files | 31 | 13 |
| `<prefix>/include` directory rules | `clang`, `clang-c`, `llvm`, `llvm-c` | **`clang-c` only** |
| `<prefix>/share/llvm/cmake` | 9 files | **absent** |
| `<prefix>/lib` distinct files | 76 | 8 |

So `-DLLVM_INSTALL_TOOLCHAIN_ONLY=ON` already removes every `LLVM*` archive,
every LLVM developer tool, the `llvm`/`llvm-c`/`clang` header trees and the LLVM
CMake package — the bulk of what the issue complains about — while keeping
`dxc`, `dxcompiler` and `include/dxc`, whose install rules are independent of it.
This is not mentioned anywhere in the issue thread.

It is not a complete answer, and the gaps are specific:

* `include/clang-c` survives, because `tools/clang/CMakeLists.txt:426` sits
  **outside** the `if (NOT LLVM_INSTALL_TOOLCHAIN_ONLY)` block that ends at
  line 424 — the same headers are installed twice, once guarded and once not;
* `libclang.lib` survives (`LIBCLANG_BUILD_STATIC ON` in
  `cmake/caches/PredefinedParams.cmake:24`);
* all seven `SPIRV-Tools*` archives, six `SPIRV-Tools*/cmake` package
  directories, `include/spirv-tools` and `lib/pkgconfig` survive — these come
  from the vendored SPIRV-Tools sub-project, which the LLVM knob does not
  govern;
* eleven of the thirteen remaining `<prefix>/bin` entries are still not the
  compiler: `dxa.exe`, `dxl.exe`, `dxopt.exe`, `dxr.exe`, `dxv.exe`,
  `SPIRV-Tools-shared.dll`, and the test binaries `HLSLErrors.exe`,
  `HLSLHost.exe`, `dxc_batch.exe`, `dxilconv-tests.dll`,
  `test_DxrFallback.exe`.

The knob is therefore a partial mitigation that a consumer could use today, not
a fix — which matters for anyone picking this up.

## Finding 3 — a supported trimmed install now exists, and DXC's own Linux CI uses it

`4f5e4d1b7` (2023-04-18, *"Setup `install-distribution` target for DXC"*, PR
#5154) added:

* `CMakeLists.txt:807-825` — `LLVM_DISTRIBUTION_COMPONENTS` defaults to
  `dxc;dxcompiler;dxc-headers` and drives an `install-distribution` target;
* `include/dxc/CMakeLists.txt:22-42` — a `dxc-headers` component listing exactly
  `config.h`, `dxcapi.h`, `dxcerrors.h`, `dxcisense.h`, plus `WinAdapter.h` on
  non-Windows (`if (NOT WIN32)`, line 29);
* `install-dxc` / `install-dxcompiler` custom targets
  (`tools/clang/tools/dxc/CMakeLists.txt:53-62`,
  `tools/clang/tools/dxcompiler/CMakeLists.txt:160-168`).

Measured (`manual-case-install-distribution.txt`), the three components install
**six files**:

```
<prefix>/bin/dxc.exe
<prefix>/bin/dxcompiler.dll
<prefix>/include/dxc/config.h
<prefix>/include/dxc/dxcapi.h
<prefix>/include/dxc/dxcerrors.h
<prefix>/include/dxc/dxcisense.h
```

That is the reporter's stated expectation — "only the dxc executable, dxc
headers and dxc libraries" — almost exactly.

It is not theoretical on Linux: `gcp-pipelines/x86_64-linux-clang.yml:36-44`
builds DXC's Linux artifact with `ninja -C build install-distribution` into
`-DCMAKE_INSTALL_PREFIX=artifacts` and zips the result.

Earliest tag containing `4f5e4d1b7`: `v1.8.2306-preview`; earliest **stable**
release: **v1.7.2308** (`git tag --contains 4f5e4d1b7 --sort=creatordate`).

**But it is undocumented.** An absence check over `*.md`, `*.rst`, `*.txt`,
`*.cmd`, `*.sh`, `*.yml` finds `install-distribution` only in `CMakeLists.txt`
itself and in that one CI file. Nothing a user reads before typing
`ninja install` mentions it. The maintainer's own comment on the issue is dated
2024-07-09 — fifteen months *after* `install-distribution` shipped — and treats
the issue as unresolved, which is consistent with the feature not being
discoverable.

## Finding 4 — the reporter's follow-up, and what it referred to

The follow-up comment says `include/dxc` "has quite a lot of stuff which isn't
dxc specific (like CMakeLists.txts and even `d3dx12.h`)". The 2020 listing shows
**no `include/dxc` in the install tree at all** — `include/dxc/CMakeLists.txt`
did not exist in the tree at the time (`git show af14220b4:include/dxc/
CMakeLists.txt` → `path ... exists on disk, but not in 'af14220b4'`), so no DXC
headers were installed. The comment therefore reads as an observation about the
**source** directory, not the installed one.

Both parts are still true of the source tree
(`git ls-files include/dxc/Support/d3dx12.h include/dxc/CMakeLists.txt` returns
both). Neither reaches the install tree now, because `include/dxc` is installed
from an explicit `install(FILES ...)` list rather than `install(DIRECTORY)`.

## Fidelity of the reporter's attachment

The gist is archived here as `reported-install-list-2020.txt` (496 lines,
fetched read-only via `gh api gists/...`). It contains `bin/dxc`, `bin/dxc-3.7`,
487 `include/clang*` / `include/clang-c` entries, and
`lib/{libdxclib.a,libdxcompiler.so,libdxcompiler.so.3.7}`.

Two things about it worth recording rather than glossing:

* It contains **no** `include/llvm*` entries and **no** `LLVM*.a`, although in
  the 2020 tree the same `NOT LLVM_INSTALL_TOOLCHAIN_ONLY` guard governed both
  the clang and the llvm header rules (`af14220b4:CMakeLists.txt:711`). The
  issue records no configure line, so the configuration that produced the
  listing cannot be reconstructed. The `result/` prefix is the Nix build-output
  convention.
* Consequently the *quantity* in the reporter's listing is not directly
  comparable with the numbers measured here. What is comparable is the
  **shape**: clang headers installed, DXC headers not.

## Why there is no predicate

`match.json` and `cmd.txt` were deliberately **not** written. Both assume one
`dxc` invocation over an HLSL source scored on its output. Every possible
compile result here — success, failure, any diagnostic — is compatible with the
report being entirely true, so a predicate built on one could not fail. Per
SKILL.md, a predicate that cannot fail is worse than none, and
`not-compiler-verifiable` is the outcome the vocabulary provides for exactly
this case. `triage.py audit` does not require either file, and no `.hlsl` exists
in the directory, so nothing is left unchecked by their absence.

The instrument-integrity check they would have provided is instead carried by
`enumerate-install-rules.py`, which prints
`# RULE-PARSE-SELFTEST=pass` only when the parser recovers the three
distribution components with the destinations a real
`cmake --install --component` produced. A parser that silently matched nothing
would otherwise be indistinguishable from a build with no install rules.

## Limitations

* **Platform.** The report is labelled `linux` and the reporter used
  `make`/`ninja`; every measurement here is Windows + Visual Studio generator.
  The rules that cause the bloat carry no platform guard, so the *finding*
  transfers; the *file list* does not. Known differences: `dxcompiler` installs
  to `lib/` rather than `bin/`
  (`tools/clang/tools/dxcompiler/CMakeLists.txt:155-158`), `WinAdapter.h` is
  added to `dxc-headers` (`include/dxc/CMakeLists.txt:29-31`), archives are
  `.a`, and the LLVM tool set differs with the generator. No Linux build was
  configured or installed.
* **Truncated dynamic runs.** The default install aborted at
  `file INSTALL cannot find .../llvm-as.exe` after 41 files, because this build
  tree has not built every tool in the Release configuration. The 41 files are a
  **lower bound**, which is why the complete answer comes from the rule
  enumeration rather than from the install run. The header-component run
  aborted the same way after 1221 files.
* **Byte sizes are configuration-specific.** For the record: 6 files / ~17 MB
  for the distribution components, versus ~625 MB for the 41 files the default
  run managed before aborting, and ~687 MB for the 1221 header/`Unspecified`
  files. These are MSVC Release static libraries and do not transfer to Linux.
* **One configuration... and one controlled pair.** `HLSL_INCLUDE_TESTS=ON` and
  `ENABLE_SPIRV_CODEGEN=ON` are responsible for the test binaries and the
  `SPIRV-Tools*` entries respectively; both are set by
  `cmake/caches/PredefinedParams.cmake:29-31`, the cache DXC ships for *nix
  builds, so they are the defaults a Linux user gets. The A/B in Finding 2 uses
  that cache on both sides and changes only `LLVM_INSTALL_TOOLCHAIN_ONLY`, so
  the deltas in that table are attributable to that one variable. Those two
  trees were **configured only** — nothing was built and nothing was installed
  from them, so their evidence is install *rules*, not files on disk.
* **No release-history sweep.** `bisect` substitutes release `dxc` binaries into
  a shader command line; it cannot exercise a CMake install target, so it was
  not run. The history statement rests on `git log` / `git tag --contains`
  instead.

## Scoring the pre-registered predicates

`expected.md` was written before any investigation. Against it:

| predicate | outcome |
| --- | --- |
| **S1** LLVM/Clang static libraries installed | **holds** — 61 `LLVM*`/`clang*`/`SPIRV-Tools*` archives by default |
| **S2** LLVM/Clang headers installed | **holds** — `include/{llvm,llvm-c,clang,clang-c}`, 1202 files measured |
| **S3** non-DXC tools installed | **holds** — 11 LLVM developer tools plus 6 test binaries |
| **S4** installed `include/dxc` carries non-header content | **fails** — `include/dxc` is now an explicit four-file `install(FILES ...)` list; `CMakeLists.txt` and `d3dx12.h` do not reach the install tree |
| **S5** no supported way to get only the DXC deliverables | **fails on "supported", holds on "documented"** — `install-distribution` produces exactly the trimmed set (Finding 3) and `LLVM_INSTALL_TOOLCHAIN_ONLY=ON` gets most of the way (Finding 2), but neither is documented anywhere a user would look |

That split is the whole reason this is `needs-human-judgement` rather than
`close-fixed`: `expected.md` set the `close-fixed` bar at "an option now exists
**and is discoverable**", and discoverability is precisely what is missing.

## Verdict

* status **`not-compiler-verifiable`** — the compiler is not the instrument
* repro quality **`partial`** — exact commands and a file listing, no configure
  line, no toolchain
* history **`unknown`** — not measurable by release probing; by source history
  the default install rules are unchanged since the report, and
  `install-distribution` has existed since v1.7.2308
* confidence **`high`** on the measurements; the open question is one of intent
* suggested action **`needs-human-judgement`**

The literal title is still accurate: the default `install` target installs
LLVM/Clang headers, archives and tools. Two things have changed since 2020 that
the thread does not record: `-DLLVM_INSTALL_TOOLCHAIN_ONLY=ON` already removes
the bulk of it (Finding 2), and the reporter's *stated expectation* is now
available exactly as a supported target, `install-distribution`, which DXC's own
Linux CI uses (Finding 3). Neither is documented anywhere a user would find it.
Whether that closes the request or merely narrows it to "document
`install-distribution`, and fix the four gaps in Finding 2" is a maintainer
call, which is why this is not filed as `close-fixed`. A standing 2024-07-09
maintainer comment also treats the issue as open.

`text_stale` was considered and **not** set. The title and body still describe
what the default target does. The follow-up comment about `include/dxc` is best
read as being about the source tree, where it remains true, so marking it stale
would be a claim about the reporter's writing that the evidence does not
support.

## Label proposal

* add **`build`** — "Issues related to build and setup"; this is entirely a
  CMake install-rule issue and `build` is what makes it findable
* add **`up-for-grabs`** — "Contributors welcome"; the maintainer comment of
  2024-07-09 says Microsoft will not spend time on it but *"we'd happily
  consider a PR that addresses this"*, which is that label's definition
* remove **`linux`** — "Linux-specific work". The rules that cause the symptom
  carry no platform guard and the bloat was reproduced here on Windows. The
  label was presumably applied because the report came from a `make install`
  user; I may be missing history behind it, so this is a proposal, not a
  correction.

`docs` was considered — the one concrete cheap action is documenting
`install-distribution` — but the issue as filed is not a documentation report,
so it is left for the maintainer rather than proposed.
