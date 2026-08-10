> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3943](https://github.com/microsoft/DirectXShaderCompiler/issues/3943).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on **all 20 stable releases** from
v1.4.1907 through v1.9.2607 — every release run individually, not just the endpoints. The
v1.4.1907 diagnostic is byte-identical to today's.

`inc/common.h` is `#pragma once` plus `float CommonValue() { return 1.0f; }`:

```hlsl
// repro.hlsl
#include "inc/common.h"   // relative to this file
#include "common.h"       // same file, via -I inc

float4 main() : SV_Target { return CommonValue(); }
```

```
> dxc -T ps_6_0 -E main -I inc repro.hlsl
In file included from repro.hlsl:10:
./inc\common.h:5:7: error: redefinition of 'CommonValue'
./inc/common.h:5:7: note: previous definition is here
```

The two paths differ only in the separator. On Windows that is DXC's own doing:
`DirectoryLookup::LookupFile` builds an `-I` candidate with `llvm::sys::path::append`
(`HeaderSearch.cpp:293-297`), which emits `\`, while a source-relative include keeps the
separator from the `#include` text. So no unusual spelling is needed to hit this — plain
`-I` versus local is enough.

**The comparison is on path strings, not file identity.** Three checks:

* Spelling the first include `"inc\common.h"` — a one-character change — compiles clean. Once
  both spellings normalise to the same string, `#pragma once` works.
* `"inc/../inc/common.h"` reproduces (the body's `Root/../MyFile.h` shape).
* `"inc/COMMON.h"` reproduces **on NTFS**, which is case-insensitive — both `#include`s read
  the same bytes and the compiler still calls them two files. That confirms the 2024-02-20
  comment about case sensitivity, and it is the clearest evidence the check never reaches the
  filesystem.

`#ifndef` guards are unaffected, as the RTX PT SDK workaround linked above assumes — but they
suppress the second inclusion's *contents*, not the second open. `-H` on a guarded twin of the
repro:

```
; Opening file [./inc/guarded.h], stack top [0]
; Opening file [./inc\guarded.h], stack top [1]
```

Mechanism: `#pragma once` is keyed on `FileEntry`
(`Pragma.cpp:356-364`), and `FileManager` uniques `FileEntry` by `UniqueID`
(`FileManager.cpp:275`) — upstream clang's inode-based uniquing, which is why this works for
C++. But `DxcArgsFileSystemImpl::GetFileInformationByHandle`
(`dxcfilesystem.cpp:468-474`) zeroes the info struct and sets
`nFileIndexLow = (DWORD)(uintptr_t)hFile`, so the "unique ID" is the handle; a handle is
reused only when `TryFindOrOpen` matches the requested path with `wcscmp`
(`dxcfilesystem.cpp:256-260`). `NormalizePathW` (`Support/Path.h:101-127`) swaps slash
direction but does not collapse `..` or case-fold. Every distinct spelling therefore gets its
own `FileEntry`.

Worth flagging for the include-handler design mentioned in the 2024-10-02 comment: matching
clang here means a notion of file identity independent of the requested path, which a custom
`IDxcIncludeHandler` serving virtual sources may not be able to supply. That is the part that
needs deciding.

Not reproducible on Compiler Explorer: it is single-file; its path is masked as `<source>`,
`#include "<source>"` cannot be resolved, and DXC warns `#pragma once in main file`, a
different rule.

Label suggestion: keep `bug`, add `usability` — the failure mode is a confusing redefinition
error rather than bad codegen, and the workaround has already propagated into shipping SDKs.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
