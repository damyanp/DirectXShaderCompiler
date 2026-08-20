# Method notes for #5309

Recorded here per the skill's per-issue boundary rule (method observations stay in this file;
they do not edit `SKILL.md` or shared scripts). Collation should read this and decide what, if
anything, generalises.

## Observation: a bare HRESULT in a generic "Conversion failed - error code 0x%08x" message is
itself a lead, not just noise

`dxbc2dxil.cpp`'s catch-all in `wmain` prints `E.hr` formatted as `0x%08x` whenever the
`hlsl::Exception`'s message string is empty -- this happens for *any* uncaught HRESULT-only
exception, regardless of which internal call produced it. Before assuming "the converter failed
on this input" (the natural reading, and the reading the maintainer's own first comment
implicitly took -- asking for "the HLSL source and FXC version or the DXBC" as if the DXBC's
content were the missing piece), it was worth decomposing the HRESULT itself:
`HRESULT_FROM_WIN32(x)` values carry `FACILITY_WIN32` in their high bits, and a Win32 error code
in the low 16 bits is directly look-up-able (`ERROR_MOD_NOT_FOUND = 126 = 0x7E` here). Grepping
the one source file that can produce the printed message for every call that returns
`HRESULT_FROM_WIN32(GetLastError())` narrowed the entire question to a single function
(`GetDxcCreateInstance`), and its very first branch (`LoadLibraryExW` returning `NULL`) is an
exact, mechanical match. This is a different shape of investigation than most crash/assert
issues in this batch: no repro needed to be run at all to get a strong, falsifiable claim about
*which* code path produced the reported number -- the number itself, decoded against the
single source file capable of emitting it, was the evidence.

**Possible generalisation for `SKILL.md`:** when an issue's only symptom is a bare
platform/HRESULT/errno-style code with no further diagnostic text, grep the emitting binary's
source for every call site that can produce a code in that number's format (`HRESULT_FROM_WIN32`,
`GetLastError()`, `errno`, etc.) before treating the code as an opaque "something failed inside
the subsystem under test." A generic-looking numeric error is sometimes the single most
specific clue in the whole report, precisely because so few call sites can produce it. Flagging
for collation's judgement; not promoting to `SKILL.md` myself per the single-writer rule.

## Observation: the #4786 harness pattern (standalone `cl.exe` compile, no CMake target
touched) generalises past ABI questions to Win32 API-mechanism questions

#4786 isolated a *hardware/ABI* mechanism (x86 float-return corrupting an x87 NaN) in a tiny
`.cpp` compiled directly with `cl.exe` via `vcvarsall.bat`, entirely outside the shared CMake
tree. The same recipe (a `-gen.py` script that runs `vcvarsall.bat && cl.exe` in one `cmd`
invocation, logs every command with `subprocess.list2cmdline`, and writes a `manual-case-*.txt`
capture) worked identically here for a completely different kind of question -- confirming a
specific Win32 API call's exact failure code (`LoadLibraryExW` + `LOAD_LIBRARY_SEARCH_
APPLICATION_DIR` on a guaranteed-absent module name) -- with zero dependency on any DXC build
target, build configuration, or catalogued release. This is a cheap, general instrument for any
issue whose reported symptom is "this specific Win32/CRT call returns this specific error
code," independent of whether the actual subsystem under test can be built or run in this
environment at all. Also flagging for collation; the two issues together (both `dxilconv`,
both in this batch) may be enough independent repetition to justify promoting "isolate the
narrow externally-checkable mechanism with a standalone `cl.exe` harness" into `SKILL.md`'s
`not-compiler-verifiable` guidance as a named technique, alongside the existing CMake-tree
parsing example (`#3276`).

## Observation: checking whether a build-system dependency gap is real, without building
anything

To judge whether the missing-DLL explanation was a plausible accident of a normal build (as
opposed to something only a badly broken build could produce), I read `AddLLVM.cmake`'s
`add_llvm_executable`/`add_llvm_tool`/`add_llvm_example` macros to confirm `EXCLUDE_FROM_ALL`
does not apply to `dxbc2dxil`/`dxilconv`, and confirmed both targets share the same
`LLVM_RUNTIME_OUTPUT_INTDIR` output directory via `set_output_directory`. This let me state with
source-level confidence that a full default build places both binaries side by side (so the
tool "just works" for a normal build), while `dxbc2dxil`'s `CMakeLists.txt` has no
`add_dependencies(dxbc2dxil dxilconv)` edge, so a *selective* build of only the `dxbc2dxil`
target does not force `dxilconv.dll` to exist. Neither half of this required building anything
-- it is pure CMake-macro and `CMakeLists.txt` reading, similar in spirit to #3276's
"parse the generated build tree instead of building it," but one level further upstream: reading
the *build system's own rules* instead of a build system's *generated output*, to answer "would
a normal build reproduce this?" without invoking a build at all.
