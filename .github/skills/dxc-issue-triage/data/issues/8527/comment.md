> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#8527](https://github.com/microsoft/DirectXShaderCompiler/issues/8527).

Confirmed. Still reproduces on `main` (1.9.0.15422, `eff900d54`), Windows/NTFS. Both ends of
the release range reproduce it too — v1.4.1907 (the oldest release with a usable `dxc`) and
v1.9.2607 — so it has been there the whole time rather than regressing.

As reported (`dxc -T cs_6_0 -E main repro.hlsl`, exit `0x80004005`):

```
In file included from repro.hlsl:6:
In file included from ./includeB.hlsli:3:
./cs_Pragma.hlsli:3:8: error: redefinition of 'Foo'
struct Foo
       ^
./cs_pragma.hlsli:3:8: note: previous definition is here
```

**But the title understates it: this is not about letter case.** Keeping the case
identical and spelling the second include `"./cs_pragma.hlsli"` fails the same way:

```
In file included from dotslash.hlsl:5:
In file included from ./includeB-dotslash.hlsli:3:
././cs_pragma.hlsli:3:8: error: redefinition of 'Foo'
struct Foo
       ^
./cs_pragma.hlsli:3:8: note: previous definition is here
```

`#pragma once` is keyed on the **path as spelled**, not on file identity. Case is just the
spelling difference Windows users hit first. `-P` shows the body emitted twice, once under
`#line 1 "./cs_pragma.hlsli"` and once under `#line 1 "./cs_Pragma.hlsli"`.

Where it comes from: `DxcArgsFileSystemImpl::TryFindOrOpen` matches an already-loaded
include by `wcscmp` on the spelled name, so a second spelling gets a second slot in
`m_includedFiles`; `GetFileInformationByHandle` then reports that slot's handle as the
file index with a zero volume serial, so `FileManager`'s `UniqueRealFiles[UniqueID]`
deduplication sees two different files and `#pragma once` is recorded against only one of
them. (`tools/clang/tools/dxcompiler/dxcfilesystem.cpp:256`, `:287`, `:468`;
`tools/clang/lib/Basic/FileManager.cpp:275`.) The `#ifndef _WIN32` branch of the same
class synthesises `st_ino` from the same handle, so this looks platform-independent —
though only Windows was measured here.

Controls: the identical repro with matching case compiles clean (exit 0, DXIL emitted), so
the failure is the spelling and nothing else. A classic `#ifndef`/`#define` include guard
also compiles clean with the case mismatch left in, which is the workaround until this is
fixed.

No Compiler Explorer link: the repro needs a header plus two includers and CE is
single-file. Folding it into one file that includes itself under a different spelling
*looks* like it works, but the same construction with a matching spelling fails
identically — both print `warning: #pragma once in main file` first, so that device
measures clang's rule that `#pragma once` is ignored in the main file, not this bug.

Suggested labels: keep `bug`, add `usability` (as reported, this rules out `#pragma once`
across a codebase) and `check-in-clang` (the defective lookup is DXC's own file-system
emulation, so the Clang HLSL front end likely does not share it — worth confirming);
remove `needs-triage`. Whether case folding, path normalisation or real file identity is
the right fix is a product decision — normalising the key would change which spelling
appears in diagnostics and dependency output.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
