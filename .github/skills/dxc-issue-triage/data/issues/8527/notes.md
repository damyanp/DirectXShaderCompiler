# #8527 — "pragma once is case sensitive" — triage notes

Ground truth: `main-debug`, Debug build of `main` at `eff900d5`, reporting
`dxcompiler.dll: 1.10(5422-eff900d5)(1.9.0.15422) - 1.9.0.15422 (main, eff900d54)`
(captured — `manual-version-main-debug.txt`; corroborated by the DXIL ident string
`dxc(private) 1.9.0.15422 (main, eff900d54)` in the clean control's own output).
Host: Windows, NTFS, per-directory case sensitivity **disabled** (measured —
`manual-case-filesystem.txt`).

**Verdict: reproduces, always has, and the title understates it.** The defect is not
case folding. `#pragma once` is keyed on the **path as spelled**, so *any* two spellings
of one file defeat it. Case is simply the spelling difference Windows users hit.

## Repro

The issue supplied all four files and the command line, so repro quality is `complete`.
`repro.hlsl` + `cs_pragma.hlsli` + `includeA.hlsli` + `includeB.hlsli` are the reporter's
structure; only the main file's name and body were minimised (the reporter's verbatim
main is kept as `as-filed.hlsl` and run separately). The one error in the report is a
typo in a file label — `cs_pragma_hlsli:` for `cs_pragma.hlsli` — which the `#include`
directives disambiguate.

`cmd.txt` departs from the report in exactly one way: **`-T cs_6_6` → `-T cs_6_0`**. The
defect is in include handling and is independent of the shader model, but no release
before v1.6.2112 accepts `cs_6_6`, so at the reported profile every older release would
be an `invalid profile` rejection — an invalid probe that fakes a regression. That is
measured, not assumed: `variant-as-filed-cs66-v1.4.1907.txt` runs the reporter's exact
command line on the oldest release and gets

```
error: invalid profile cs_6_6
```

which `triage.py` scores `invalid-probe`. Had the bisection been run at `cs_6_6` it would
have reported a false "fixed in an old release, regressed later" history. The reporter's
exact configuration is preserved in `cmd-as-filed.txt` and measured on ground truth as
`variant-as-filed-main-debug.txt`, which fails identically to the retargeted repro.

## What was measured

| what | file | exit | result |
| --- | --- | --- | --- |
| repro, `-T cs_6_0` | `out-main-debug.txt` | 0x80004005 | `error: redefinition of 'Foo'` |
| reporter's main verbatim, `-T cs_6_6` | `variant-as-filed-main-debug.txt` | 0x80004005 | same error |
| **control:** matching case | `variant-control-samecase-main-debug.txt` | **0** | clean DXIL, no error |
| minimised to 2 files | `variant-direct-main-debug.txt` | 0x80004005 | same error |
| **same case, `./` spelling** | `variant-dotslash-main-debug.txt` | 0x80004005 | same error |
| `#ifndef` guard instead of `#pragma once` | `variant-ifndef-guard-main-debug.txt` | **0** | clean DXIL |
| `-P` preprocess | `variant-preprocess-main-debug.txt` → `preprocessed-repro.i` | 0 | body emitted twice |
| v1.4.1907 (bisect floor) | `out-v1.4.1907.txt` | 0x80004005 | same error |
| v1.9.2607 (newest) | `out-v1.9.2607.txt` | 0x80004005 | same error |
| reporter's `cs_6_6` on v1.4.1907 | `variant-as-filed-cs66-v1.4.1907.txt` | 0x80004005 | `invalid profile cs_6_6` — **invalid probe**, why `cmd.txt` retargets |

Ground truth, verbatim:

```
In file included from repro.hlsl:6:
In file included from ./includeB.hlsli:3:
./cs_Pragma.hlsli:3:8: error: redefinition of 'Foo'
struct Foo
       ^
./cs_pragma.hlsli:3:8: note: previous definition is here
```

`0x80004005` is E_FAIL, dxc's ordinary diagnosed-error status on Windows — **not** an
internal failure. Nothing here is crash-shaped.

## The finding the title misses

`dotslash.hlsl` keeps the case identical throughout and spells the shared header
`"./cs_pragma.hlsli"` in the second chain. It reproduces:

```
In file included from ./includeB-dotslash.hlsli:3:
././cs_pragma.hlsli:3:8: error: redefinition of 'Foo'
./cs_pragma.hlsli:3:8: note: previous definition is here
```

`././cs_pragma.hlsli` and `./cs_pragma.hlsli` are the same file by any definition, on any
filesystem. So the report's framing — "case sensitive" — describes the symptom, not the
defect. **`#pragma once` is keyed on the spelled path.** That matters for the fix: case
folding alone would not be enough.

`-P` shows it directly (`preprocessed-repro.i`): `struct Foo` is emitted twice, once
under `#line 1 "./cs_pragma.hlsli"` and once under `#line 1 "./cs_Pragma.hlsli"`.

## Mechanism, from source

The chain is complete and each step is a one-line read:

1. `DxcArgsFileSystemImpl::TryFindOrOpen` matches an already-loaded include with
   `wcscmp` against the **name as spelled** — case-sensitive, no normalisation
   (`tools/clang/tools/dxcompiler/dxcfilesystem.cpp:256-262`). A miss loads the file
   again into a new slot: `m_includedFiles.emplace_back(std::wstring(lpFileName), ...)`
   (`:287`). The only path munging on the way in is
   `MakeAbsoluteOrCurDirRelativeW`, which prepends `./` and nothing else (`:158-166`) —
   it does not canonicalise, which is why `././x` gets its own slot.
2. `CreateFileW` returns `IncludedFileIndexToHandle(includedIndex)` — a handle encoding
   the slot index (`:450-453`, `:307`).
3. `GetFileInformationByHandle` zeroes the struct and sets
   `nFileIndexLow = (DWORD)(uintptr_t)hFile`, leaving `dwVolumeSerialNumber` and
   `nFileIndexHigh` at 0 (`:468-478`). The file's "identity" is therefore its slot, not
   the file.
4. `sys::fs::status` builds `file_status` from those fields
   (`lib/Support/Windows/MSFileSystem.inc.cpp:630-634`) and
   `file_status::getUniqueID()` composes `UniqueID(VolumeSerialNumber, FileIndex)`
   (`:326-332`) — distinct per slot.
5. `clang::FileManager::getFile` deduplicates through `UniqueRealFiles[Data.UniqueID]`
   (`tools/clang/lib/Basic/FileManager.cpp:275`), the mechanism whose own comment says
   "See if we have already opened a file with the same inode". Two synthetic UniqueIDs
   mean two `FileEntry`s.
6. `#pragma once` lives in `HeaderFileInfo`, indexed by `FileEntry::getUID()`, so the bit
   set for one spelling is invisible to the other.

The same `DxcArgsFileSystemImpl` is compiled on Linux: the `#ifndef _WIN32` block at
`dxcfilesystem.cpp:723-796` reimplements `stat` over the *same* synthetic handles
(`Status->st_dev = Info.nFileIndexHigh; Status->st_ino = Info.nFileIndexLow;` at `:753`),
and `file_status::getUniqueID()` there is `UniqueID(fs_st_dev, fs_st_ino)`
(`lib/Support/Unix/Path.inc:185-187`). **This is a source-based inference, not a
measurement** — see "What was not determined".

## History

`bisect` — endpoints agree, so it short-circuited: **always-repro'd across
v1.4.1907..v1.9.2607**, the full checkable range. v1.4.1907 is the bisection floor, so
this means "for as long as it is possible to check", not "since HLSL had `#pragma once`".
Both endpoint probes are valid: each compiled the repro and emitted the reported
diagnostic, so neither is an `invalid-probe`.

Not a regression. Nothing to attribute.

## Workaround

`guarded.hlsl` replaces `#pragma once` with a classic `#ifndef`/`#define` guard, keeping
the case mismatch. It compiles clean (exit 0), because the guard macro is global to the
translation unit and does not depend on file identity. That is measured, not assumed.

## Compiler Explorer

No link. The repro needs at least a header and two includers; CE is single-file. CE also
runs Linux, where `cs_Pragma.hlsli` genuinely does not exist, so the reported form could
not run there even with the files.

The obvious workaround was tried and **rejected**. `example.hlsl` has the file include
itself as `"./example.hlsl"` — a different spelling of the path the driver was given —
and it does emit `error: redefinition of 'Foo'` locally and on both CE DXC panes. But
`selfsame.hlsl` is the same construction with a *matching* spelling and it fails
identically (`variant-selfinclude-samespelling-main-debug.txt`,
`manual-case-godbolt.txt`). The device measures clang's documented rule that
`#pragma once` is ignored in the main file — both the local build and both CE DXC panes
print `warning: #pragma once in main file` (clang's `-Wpragma-once-outside-header` group)
before the error — and says nothing about #8527. Both files are kept, labelled, so
nobody rebuilds the same dead end.

## What was not determined

- **Linux behaviour is not measured.** Everything above is Windows/NTFS. The source
  reading in "Mechanism" says the same code runs on Linux, but no Linux binary was run,
  and the one probe that reached a Linux build (CE) was invalidated by its own control.
  A Linux check of the `./`-spelling form would settle it in one command.
- **`IDxcIncludeHandler` API users are not measured.** The defective lookup is in
  `DxcArgsFileSystem`, which is also the path an embedding application's include handler
  goes through, so the same double-load is plausible there — untested.
- **Which fix is right is a maintainer call.** Normalising the lookup key would change
  which spelling appears in diagnostics and in `-Vi`/dependency output; deduplicating on
  real file identity would need `DxcArgsFileSystem` to carry one, which it currently does
  not for in-memory includes. Not pre-empted here.

## Side observation, out of scope

`-Vi` ("Display details about the include process", per `dxc --help`) printed nothing at
all on either the failing repro or a clean compile —
`variant-show-includes-main-debug.txt`. It would have been the natural way to show the
double load. Unrelated to #8527 and not investigated further.
