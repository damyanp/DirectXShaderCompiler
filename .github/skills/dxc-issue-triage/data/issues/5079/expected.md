# Expected symptom -- #5079 "Conflict with DirectX-Headers"

Written before any probe is run (step 2). Derived from the issue body and its
error log only.

## What the reporter did

On Linux, building a project that:

1. links a released `dxc`/`libdxcompiler` and includes DXC's public header
   `dxc/dxcapi.h` (which on non-Windows pulls in DXC's own
   `include/dxc/WinAdapter.h`, a from-scratch shim that defines Windows base
   types -- `BYTE`, `BOOLEAN`, `BOOL`, `LONG`, `ULONG`, `LONGLONG`,
   `LONG_PTR`, `ULONG_PTR`, `ULONGLONG`, `_GUID`/`GUID`, `REFGUID`,
   `REFCLSID`, etc. -- for a platform that has none of them), and
2. also builds against DirectX-Headers, which for non-Windows targets ships
   its *own*, independently-written shim providing the identical set of
   Windows base types (in the reporter's version, `wsl/stubs/basetsd.h`; in
   older DirectX-Headers releases the same content lived in one file,
   `wsl/winadapter.h` -- confirmed identical in kind by both files' content
   and by PR #8431's own investigation, see below),

gets a wall of `clang` errors of the shape `typedef redefinition with
different types (...)` for exactly those types, plus `redefinition of
'_GUID'`, because the two shim headers disagree on the underlying type for
several of them (e.g. `BOOL` as `bool` in DXC's copy vs. `uint32_t`/`BOOL`-as-
integer in DirectX-Headers' copy; `BOOLEAN` as `char` vs. `unsigned char`).

## What "this reproduces" means

A minimal C++ translation unit that, under a **non-Windows** preprocessor
configuration (`_WIN32` undefined -- the condition both shims are gated on):

- includes DirectX-Headers' non-Windows Windows-type shim (providing `BYTE`,
  `BOOLEAN`, `BOOL`, `LONG`, `ULONG`, `LONGLONG`, `LONG_PTR`, `ULONG_PTR`,
  `ULONGLONG`, `GUID`, `REFGUID`, `REFCLSID`, ...), then
- includes DXC's own `dxc/dxcapi.h` (which unconditionally pulls in
  `dxc/WinAdapter.h`, defining the *same* names again with possibly
  different underlying types),

fails to compile with `typedef redefinition with different types` /
`redefinition of '_GUID'` diagnostics naming those symbols -- the same class
of error quoted in the issue body, even if the exact source paths and the
exact DirectX-Headers version differ from the reporter's.

**Does not reproduce** would mean: this combination compiles cleanly, i.e.
DXC's `WinAdapter.h` no longer independently redefines a type that
DirectX-Headers' non-Windows shim already provides (for example, by having
one shim `#include` the other, guard its own definitions, or reuse the
other's typedefs) -- which is the shape of the fix under discussion in PR
#8431 ("Update DirectX-Headers to latest").

## Repro quality

`complete`. The issue supplies an exact 3-line repro file and an exact,
complete compiler error transcript naming every conflicting symbol. The
local reconstruction below is not agent-invented: it uses the exact
`include/dxc/WinAdapter.h` this repository ships and the exact non-Windows
shim (`external/DirectX-Headers/include/wsl/winadapter.h`) the pinned
`DirectX-Headers` submodule ships, so the same two authors' code is
exercised, not an approximation of it. The one honest gap: the reporter's
DirectX-Headers release (v1.608.2) had already split this shim into
`wsl/stubs/basetsd.h` plus siblings, while the pinned submodule
(`980971e8`, from 2022-01-31, unchanged since commit `14a55b773`) still
carries the pre-split, single-file `wsl/winadapter.h`. PR #8431's author
(`amaiorano`) independently investigated and confirmed the two are the same
content relocated, not a different defect (quoted verbatim in `notes.md`).

## Is `dxc.exe` the instrument here?

No. This is not a shader-compilation question and `cmd.txt`/`match.json`
(dxc-driven, HLSL-file probes) do not apply -- there is no `.hlsl` input and
no release-by-release `dxc` bisection to run; every stable release ships the
same DXC-side `WinAdapter.h` design (its own from-scratch shim), and the
reporter's conflict is with a *different* project's headers entirely.
`clang`, compiling this repository's own vendored header tree, **is** a
faithful instrument for the question and is used as one, captured under
`manual-case-*.txt` per the skill's convention for a non-`dxc` repro.
