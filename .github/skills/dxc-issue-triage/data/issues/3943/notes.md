# 3943 — `#pragma once` cannot support path aliases

**Verdict: reproduces on `main`, and on every stable release that can be tested.**

## The claim

Filed 2021-09-10 by `Ceffa93`. With `-I <path>` on the command line, the same physical header
can be named by two different path spellings; `#pragma once` treats the two spellings as two
different files, so the header is included twice.

Two later comments extend it: `otanter-at-ubi` (2024-02-20) reports the aliasing is also
case-sensitive, and `oscarbg` (2024-05-05) reports the bug hit in NVIDIA's RTX Path Tracing
SDK, linking that codebase's `#ifndef` workaround. `damyanp` (2024-10-02) states the intended
behaviour: *"We expect that this will work in HLSL in clang as well as it works for C++ in
clang."*

Repro quality: **partial**. The two include spellings are given, and the mechanism is stated
precisely, but there is no header, no shader, no command line and no output. Everything below
is agent-constructed from that description.

## What was tested

Double inclusion is not directly observable, so the header defines something that cannot
legally be defined twice and the symptom is the compiler rejecting the second definition.

`inc/common.h` is `#pragma once` plus `float CommonValue() { return 1.0f; }`.
`inc/guarded.h` is the same body behind `#ifndef INC_GUARDED_H`.

`cmd.txt` runs **two** invocations, and `match.json` is the conjunction of one clause from
each:

| # | invocation | required in output |
| --- | --- | --- |
| 1 | `-T ps_6_0 -E main -I inc control-once.hlsli` | `define void @main()` |
| 2 | `-T ps_6_0 -E main -I inc repro.hlsl` | `redefinition of 'CommonValue'` |

Clause 1 is the instrument self-test, and it is a scored clause rather than prose on purpose:
`'inc/common.h' file not found` is an ordinary diagnosed error, not one of `classify()`'s
feature-absence markers, so a release that could not resolve `-I` would emit no redefinition,
score a confident `no-repro`, and invent a fix boundary. Because the predicate is a
conjunction, **every `repro` verdict below is proof that the self-test passed in the same
run** — no invalid probe is possible in the match direction, now or after any future
re-scoring.

### Result on ground truth

`main-debug`, `1.9.0.5433`, a clean Debug build of `main` at `13730886e`. (The binary
self-reports the fork-local SHA `ab5400907`; `git diff --name-only` between the two shows no
file outside this skill's directory, and the same command against `13730886e~200` shows 581,
so the control confirms the comparison is capable of finding a difference.)

`out-main-debug.txt`, exit `2147500037` = `0x80004005` (`E_FAIL` — an ordinary diagnosed
error, not an internal compiler failure):

```
In file included from repro.hlsl:10:
./inc\common.h:5:7: error: redefinition of 'CommonValue'
./inc/common.h:5:7: note: previous definition is here
```

The two paths in that pair differ **only in the separator**, which is the whole finding in one
line: `./inc\common.h` and `./inc/common.h` are the same file, and the compiler is treating
them as two.

### Control matrix

Every control is a tool-made capture with a declared `--expect`, all satisfied.

| file | difference from repro | verdict | shows |
| --- | --- | --- | --- |
| `repro.hlsl` | — | **repro** | claim A: `-I` arm vs source-relative arm |
| `alias-dotdot.hlsl` | second include is `inc/../inc/common.h` | **repro** | claim B: the body's literal `Root/../MyFile.h` shape |
| `alias-case.hlsl` | second include is `inc/COMMON.h` | **repro** | claim C: case, on **case-insensitive NTFS** |
| `control-single.hlsl` | one include | no-repro | the predicate does not fire on innocent code |
| `control-guard.hlsl` | header uses `#ifndef` | no-repro | the thread's workaround is immune |
| `control-separator.hlsl` | first include spelled `inc\common.h` | no-repro | **one character** decides it |

The last two rows are the informative ones.

`control-separator.hlsl` differs from `repro.hlsl` by a single character — the separator in
the first `#include` — and it compiles clean. Once both spellings normalise to the identical
string, the second include is suppressed. So the mechanism is a comparison of path *strings*,
not of file identity.

Claim C reproducing on Windows says the same thing from the other side. NTFS is
case-insensitive: `inc/COMMON.h` and `inc/common.h` are one file to the operating system, and
both `#include`s read the same bytes. The compiler still treats them as two, so the comparison
never reaches the filesystem at all.

### The include trace shows the double open directly

`-H` prints nothing on a failing compile, so the trace was taken on `control-guard.hlsl` —
the same two spellings as the repro, but a guarded header, so it compiles
(`variant-include-trace-two-spellings-main-debug.txt`):

```
; Opening file [./inc/guarded.h], stack top [0]
; Opening file [./inc\guarded.h], stack top [1]
```

Two opens of one file. The matched-spelling control shows one
(`variant-include-trace-one-spelling-main-debug.txt`). This also shows that the `#ifndef`
workaround suppresses the *contents* of the second inclusion, not the second open — the file
identity confusion is present either way; guards just don't depend on file identity.

## History

`bisect --linear` over the release population: **all 20 stable releases reproduce**, from
v1.4.1907 (2019, the floor of what is checkable) through v1.9.2607. Not endpoints — every
release was run.

Excluded, and why: `v1.2.0-alpha` has no usable dxc asset; five prereleases (`v1.5.2003`,
`v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`, `v1.10.2605.2`, `v1.10.2605.24`) are
skipped by policy and the issue names no prerelease, so there is no reason to opt in.

So the history value is `always-repro'd`, understood as *"for as long as it is possible to
check"* — the issue was filed in 2021, comfortably inside the tested range, so the report has
never described anything but current behaviour. v1.4.1907's diagnostic is **byte-identical**
to `main`'s, seven years apart, which is worth stating plainly: nothing about this has moved.

## Corroboration from source

The behaviour is fully explained by three facts in the tree, and the controls above test the
prediction each one makes rather than merely illustrating it.

1. `#pragma once` state is per-`FileEntry`. `Preprocessor::HandlePragmaOnce` calls
   `HeaderInfo.MarkFileIncludeOnce(...getFileEntry())`
   (`tools/clang/lib/Lex/Pragma.cpp:356-364`), and `ShouldEnterIncludeFile` reads
   `HFI.isPragmaOnce` (`tools/clang/lib/Lex/HeaderSearch.cpp:1024`). So everything depends on
   whether two spellings produce one `FileEntry`.

2. `FileManager` uniques by `UniqueID` — `UniqueRealFiles[Data.UniqueID]`
   (`tools/clang/lib/Basic/FileManager.cpp:275`). That is upstream clang's inode-based
   uniquing, and it is why this works for C++ in clang. On Windows the ID is built from
   `dwVolumeSerialNumber` and `nFileIndex{High,Low}`
   (`lib/Support/Windows/MSFileSystem.inc.cpp:326-332`).

3. dxc does not supply those numbers from the filesystem.
   `DxcArgsFileSystemImpl::GetFileInformationByHandle`
   (`tools/clang/tools/dxcompiler/dxcfilesystem.cpp:468-474`) zeroes the structure and sets
   `nFileIndexLow = (DWORD)(uintptr_t)hFile`, leaving `nFileIndexHigh` and
   `dwVolumeSerialNumber` at 0. The "unique ID" is therefore **the handle**. Handles index
   `m_includedFiles`, and a new one is issued unless `TryFindOrOpen` finds an existing entry
   with `0 == wcscmp(lpFileName, m_includedFiles[i].Name.data())`
   (`dxcfilesystem.cpp:256-260`) — a case-sensitive raw comparison of the requested path
   string.

   The only normalisation in play is `hlsl::NormalizePathW`
   (`include/dxc/Support/Path.h:101-127`), which swaps slash direction, collapses double
   slashes and prefixes `./`. It does not collapse `..`, does not case-fold, and is applied to
   the string handed to the loader rather than to the `wcscmp` key.

   Predictions, all confirmed above: `..` aliases (B), case aliases even on a case-insensitive
   volume (C), and two spellings that normalise to one string do **not** alias
   (`control-separator`).

The stray backslash in the diagnostic is the fourth piece.
`DirectoryLookup::LookupFile` builds an `-I` candidate with
`llvm::sys::path::append(TmpDir, Filename)` (`tools/clang/lib/Lex/HeaderSearch.cpp:293-297`),
and `path::append` uses `\` on Windows, whereas a source-relative include keeps whatever
separator the `#include` text used. That is why `-I` and local spellings of one file differ by
a separator and hence by identity — i.e. on Windows the issue's headline case is triggered by
DXC's own path construction, not by anything the user wrote.

No HLSL-side test in `tools/clang/test/` asserts `#pragma once` behaviour, so a fix would not
have to change an existing expectation.

## Assessment

- **Status: reproduces.** Confidently, on `main` and on all 20 checkable stable releases.
- **Broader than the title.** "Path aliases" undersells it: any two spellings that are not
  `wcscmp`-identical after slash normalisation are different files to `#pragma once`. That
  includes case on a case-insensitive volume, and — because of `path::append` — the plain
  `-I`-versus-local pairing the issue reports, with no unusual spelling from the user at all.
- **Not text-stale.** The body describes what the compiler does; the mechanism note above is
  an addition, not a correction.
- **Suggested action: `still-valid-keep-open`.** A maintainer has already stated the intended
  behaviour and pointed at the include-handler redesign as the place to address it, so the
  next step is a design decision, not a verdict.
- **Labels: keep `bug`, add `usability`.** It has a silent-ish failure mode and a workaround
  the ecosystem has already adopted (NVIDIA's RTX PT SDK), which is a usability cost rather
  than a codegen defect.

  Deliberately *not* proposed: `low-hanging-fruit` / `up-for-grabs`, because the fix has to
  decide what identity means for `IDxcIncludeHandler`, where a custom handler may serve
  virtual files that have no filesystem identity at all — a design question, not a patch;
  `check-in-clang`, since the maintainer comment already frames the expectation in clang terms;
  and `high-impact`, which is a prioritisation call for a maintainer, so the impact evidence
  belongs in the comment instead.

## Compiler Explorer

Skipped, with the reason measured rather than assumed —
`manual-case-ce-infeasible.txt`, regenerable with `ce-probe.py`. CE is single-file and this
repro needs a header plus `-I`. The obvious fold (a file including itself under two spellings)
does not work either: CE masks the pane's path as `<source>`, `#include "<source>"` cannot be
resolved, and DXC emits `warning: #pragma once in main file` — the compiler pointing out that
the main file is governed by a different rule. The fold's known-good control fails identically,
which is what makes the transformation invalid rather than merely unlucky.

## Deviations from `expected.md`

Both were forced by the plan meeting the filesystem, and neither changes what is claimed:

- Claim B was planned as `inc/sub/../common.h`, which needs an empty `inc/sub/` directory —
  and git cannot store one, so the committed repro would fail for a reader for a reason
  unrelated to the bug. Built as `inc/../inc/common.h` instead: same `..` semantics, and every
  directory it traverses already contains tracked files.
- The self-test file is `control-once.hlsli`, not `.hlsl`, so that `run --shader` retargets
  only the repro line. See `method-notes.md`; it is load-bearing.

`control-separator.hlsl` was not planned at all. It came out of a calibration probe that
noticed the backslash in the diagnostic, and it turned out to be the sharpest control here, so
it was promoted from scratch file to declared control.

## Runnable from the repo alone

Verified, not assumed. The directory was reconstructed from
`git ls-files --others --exclude-standard` — exactly the bytes a fresh clone would hold, 47
files, none gitignored — into a scratch tree, and `cmd.txt` was run there: the self-test exited
0 with DXIL and the repro produced the identical `./inc\common.h` / `./inc/common.h`
diagnostic. No directory this repro needs is empty, so there is nothing for git to drop.
