# Method notes from #5072

Observations about the workflow and tooling, not about the issue itself.

## 1. Before designing a release matrix, read *where* the affected code lives

#3237's `measure.py` swapped `dxcompiler.dll` under a fixed harness `.exe`
because that issue's bug (a reflection getter) lives inside the DLL. #5072's
bug is the opposite shape: `-Fh`'s header-writing code
(`DxcContext::WriteHeader`) lives in `tools/clang/tools/dxclib/dxc.cpp`,
statically linked into the **driver executable**, not the DLL. A DLL-swap
harness would have silently tested only ground truth's own driver logic
against every release's *compiler core*, answering a question nobody asked.

The fix was cheap once noticed (`fh-header-check.py` already took the real
`dxc.exe` path from an env var, so `release-matrix.py` just points that var
at each release's whole `dxc.exe` instead of swapping a DLL), but the design
choice is easy to get backwards by pattern-matching #3237 without checking.
**Generalisable rule:** before writing a release-matrix script, `grep` for the
symbol/behaviour under test and note whether its translation unit ends up in
`dxcompiler.dll` or in the `dxc`/`dxclib`-only object files. That one fact
picks the whole harness shape.

## 2. A file-only output flag needs an explicit check for CE, not just an assumption

`-Fh`'s target is a natural `godbolt --skip` candidate — CE's
`/api/compiler/.../compile` only returns `stdout`/`stderr`/`asm` text, with no
channel for an arbitrary file a flag asked the compiler to write. That much
is structural and predictable from reading `ce_compile()`.

What is *not* predictable without checking: whether the defect leaks into the
`asm`/disassembly text some other way (e.g. as a comment, a debug-info string,
or a name baked into an exported symbol) even though its primary artifact is
file-only. For #5072 I confirmed empirically — default disassembly of the
same repro at `-T lib_6_3` with **no** `-Fh` at all contains no occurrence of
`lib.no::entry` anywhere — before writing the skip reason. Skipping on the
structural argument alone would have been the right call here too, but only
by luck; a defect whose sentinel *did* leak into a comment line would make
"CE cannot show this" simply false. **Check the plain-compile output for the
symptom before writing a `--skip` reason that says it cannot appear there.**

## 3. `cl.exe` needs no `vcvars64.bat` for a single, `#include`-free header

Confirming "does the generated header actually fail to compile" only needed
`cl.exe /nologo /c /TC|/TP <header>` run directly — no `vcvars64.bat`, no
environment setup, and none of #3237's parenthesis/`vswhere.exe` batch-file
trap (method-notes.md #3 there) applied, because there was no `.cmd` wrapper
to write in the first place. This only holds for a translation unit with no
`#include`s that need the MSVC/Windows SDK search paths `vcvars64.bat`
otherwise sets up; anything that includes system headers would still need
the full environment. Worth remembering as the cheaper path when the
question is only "is this token sequence legal C/C++", not "does this
program run".
