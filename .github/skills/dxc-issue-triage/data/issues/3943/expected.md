# 3943 — "#pragma once cannot support path aliases"

Written **before** running the compiler.

## What the issue says

Opened 2021-09-10 by `Ceffa93` (Filippo Ceffa). Label: `bug`. Body, in full:

> By using the `-I <path>` flag, it is possible to specify an additional root folder in which
> to look for headers. This means that the same file can be included as:
>
> ```
> #include "MyFile.h" // local include
>  #include "Root/../MyFile.h" // absolute include from the specified path
> ```
>
> `#pragma once` considers the two paths above as different, and this causes the same file to
> be included twice.

Three comments:

* 2024-02-20, `otanter-at-ubi`: *"maybe related, it is also case sensitive, which may or may
  not be a bug."*
* 2024-05-05, `oscarbg`: reports the same issue hit in NVIDIA's RTX Path Tracing SDK, and
  links the workaround in that codebase — `#ifndef __INLINE_SAMPLE_GENERATORS_HLSLI__ //
  using instead of "#pragma once" due to <this issue>`.
* 2024-10-02, `damyanp` (maintainer): *"We expect that this will work in HLSL in clang as well
  as it works for C++ in clang. @coopp, something to consider here when designing the new
  include handler API."*

So the thread is not disputed: a maintainer states the intended behaviour is clang's, and
points at the include-handler redesign as where it should be addressed.

**Repro quality in the issue: `partial`.** The two include spellings are given as code, and
the mechanism is stated precisely, but there is no header, no shader, no command line and no
captured output. Every file used below is agent-constructed from that description.

## What "this reproduces" means

The reported symptom is *double inclusion of a `#pragma once` header when the same physical
file is named by two different path spellings*. Double inclusion is not directly observable;
its consequence is, so the repro makes the header define something that cannot legally be
defined twice, and the symptom is present when the compiler rejects the second definition.

**Symptom present** when, with `-I inc` on the command line and a header carrying
`#pragma once`:

1. compiling a shader that includes that header **once by each of two spellings** fails with
   a redefinition diagnostic naming the header's function; **and**
2. in the same run, the control that includes the header **twice by the identical spelling**
   compiles successfully and emits DXIL — proving `#pragma once` works in this build, that
   `-I` resolution works, and that the header was reachable.

Clause 2 is the instrument self-test and it is a *required* clause, not prose. Without it a
release that simply cannot find `inc/common.h` emits no redefinition either, scores clean, and
manufactures a fix boundary. A release where clause 2 fails is **unmeasurable** under this
predicate, not `no-repro`; the capture holds both invocations, so which one it is can always
be read off the file.

## What would falsify it (i.e. "does-not-repro" / "fixed")

The two-spelling shader compiling successfully and emitting DXIL, with no redefinition
diagnostic — i.e. the second `#include` being suppressed by `#pragma once` exactly as the
same-spelling control's second `#include` is.

Note what is **not** falsification: a compile that fails for some other reason (header not
found, unknown profile, bad flag). That is an invalid probe, and clause 2 is what exposes it.

## Sub-claims to score separately

The thread contains three distinct spellings-that-alias, and they need not resolve the same
way. Each is scored on its own capture:

| # | claim | source | spelling pair |
| --- | --- | --- | --- |
| A | two different *search paths* reach one file | issue body, first sentence | `#include "inc/common.h"` (relative to includer) vs `#include "common.h"` (found via `-I inc`) |
| B | a path containing `..` aliases the same file | issue body's literal `"Root/../MyFile.h"` | `#include "inc/common.h"` vs `#include "inc/sub/../common.h"` |
| C | differing **case** aliases the same file on a case-insensitive filesystem | otanter-at-ubi's comment | `#include "inc/common.h"` vs `#include "inc/COMMON.h"` |

A is the primary repro (it is what the body's prose describes and what `-I` is for). B and C
are labelled variants. C is explicitly filesystem-dependent: the ground truth here is Windows,
where NTFS is case-insensitive, so the two spellings do name one file. On a case-sensitive
filesystem they would not, and no verdict about C can be carried to Linux from this run.

The workaround the thread already uses (`#ifndef` guards instead of `#pragma once`) is worth a
control too: guards are keyed on a macro name rather than on file identity, so they should be
immune. If they are not, the finding is much larger than the issue claims.

## Where to look in the tree (claims to check, before measuring)

`#pragma once` state is per-`FileEntry`: `Preprocessor::HandlePragmaOnce` calls
`HeaderInfo.MarkFileIncludeOnce(getCurrentFileLexer()->getFileEntry())`
(`tools/clang/lib/Lex/Pragma.cpp:356-364`), and `HeaderSearch::ShouldEnterIncludeFile` reads
`HFI.isPragmaOnce` (`HeaderSearch.cpp:1024`). So the question is entirely *whether two
spellings produce one `FileEntry`*.

`FileManager::getFile` uniques by `Data.UniqueID` — `UniqueRealFiles[Data.UniqueID]`
(`tools/clang/lib/Basic/FileManager.cpp:275`), which is upstream clang's inode-based uniquing
and is exactly why this works in C++ clang. `Data.UniqueID` comes from
`vfs::Status::getUniqueID()` (`FileSystemStatCache.cpp:27`), and on Windows that is
`UniqueID(VolumeSerialNumber, FileIndexHigh<<32 | FileIndexLow)`
(`lib/Support/Windows/MSFileSystem.inc.cpp:326-332`).

The candidate defect is that dxc does not go to the real filesystem for those numbers.
`DxcArgsFileSystemImpl::GetFileInformationByHandle`
(`tools/clang/tools/dxcompiler/dxcfilesystem.cpp:468-478`) zeroes the structure and sets
`nFileIndexLow = (DWORD)(uintptr_t)hFile` — the *handle*, not the file index — leaving
`nFileIndexHigh` and `dwVolumeSerialNumber` at 0. The handle is an index into
`m_includedFiles`, and `TryFindOrOpen` finds an existing entry with
`0 == wcscmp(lpFileName, m_includedFiles[i].Name.data())` (`dxcfilesystem.cpp:256-258`) — a
**case-sensitive comparison of the requested path string**. The only normalisation applied is
`hlsl::NormalizePathW`, which swaps slash direction, collapses double slashes and prefixes
`./` (`include/dxc/Support/Path.h:101-127`) — it does not collapse `..` and does not case-fold,
and it is applied to the string handed to the include loader, not to the key used for the
`wcscmp` above.

If that reading is right, then every distinct spelling gets its own entry, its own handle, its
own `UniqueID` and therefore its own `FileEntry`, and `#pragma once` cannot possibly work
across spellings. Predictions that follow, all of which the measurement can falsify:

* A and B reproduce;
* C reproduces on Windows *even though the filesystem is case-insensitive*, because the
  comparison is `wcscmp` and never reaches the filesystem;
* `#ifndef` guards are unaffected;
* the behaviour is old — this code is not recent — so expect `always-repro'd` rather than a
  regression.

Also to check before bisecting: does `tools/clang/test/` already assert this behaviour, and is
there a test that a fix would have to change?

## Planned probes

| probe | what it decides |
| --- | --- |
| `cmd.txt` line 1: `-T ps_6_0 -E main -I inc control-once.hlsl` | in-predicate self-test: `#pragma once` works, `-I` resolves, header reachable |
| `cmd.txt` line 2: `-T ps_6_0 -E main -I inc repro.hlsl` | claim A, the repro |
| variant `dotdot` | claim B |
| variant `case` | claim C (Windows only) |
| variant `guard` (`--expect no-match`) | the thread's workaround really is immune |
| variant `single` (`--expect no-match`) | negative control: one include of the header does not fire the predicate |
| `bisect --linear` | history across stable releases |

## Predicate hazards I expect to have to handle

* The symptom is a **diagnostic**, so an error in the output is both the signal and the thing
  `classify` treats as a bad probe. `redefinition of` is not one of its feature-absence
  markers, but every capture's `# invalid-probe-reason:` must still be read.
* `'inc/common.h' file not found` is an ordinary diagnosed error, **not** a feature-absence
  marker, so a release that cannot resolve the include would score `no-repro` and read as a
  fix. Clause 2 of the predicate exists precisely to stop that.
* The multi-file repro must be runnable from the repo alone. Git does not store empty
  directories, so every directory this repro needs must contain a tracked file; nothing may
  depend on a directory the compiler or the operator creates by hand.
* The diagnostic's exact wording is not guaranteed portable across release ages. Anchor
  loosely on `redefinition of ... CommonValue` and check the oldest release's capture before
  trusting a `no-repro`.
* Compiler Explorer is **single-file**, so it cannot host a two-file repro at all. The obvious
  fold — a file that includes itself under two spellings — measures a different rule, because
  clang ignores `#pragma once` in the main file. If CE cannot show this, record a measured
  skip rather than publishing a link that shows nothing.

## History question

If the source reading above is right this has never worked in any shipped dxc, and the correct
history value is `always-repro'd` (understood as "for as long as it is possible to check",
floor v1.4.1907). Use `--linear`: the claim being made is about the whole release population,
and endpoint agreement alone does not support that.
