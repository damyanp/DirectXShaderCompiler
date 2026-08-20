# Expected behavior (written before running anything)

Issue: "[MacOS only] dxc dump nothing when -fcgl with root signature" (#5476).

Reporter's exact repro: `dxc -Tcs_6_0 -fcgl` on a compute shader that has a
`[RootSignature("DescriptorTable(SRV(t0), UAV(u0))")]` attribute on the entry
point. Reported (macOS only) actual behavior: **nothing is dumped to the
console** -- the process runs but no `-fcgl` (unoptimized codegen / "-Vd"-style
early IR dump) text appears. The reporter attributes this to
`UTF8BufferToWideBuffer` failing on the *serialized root signature bytes*
that get embedded in the dumped module (raw/binary bytes are not valid UTF-8,
so the UTF-8 -> UTF-16 conversion used by the console-writing path fails and
the wide buffer stays null, which the `WriteWideNullTermToConsole` helper
silently no-ops on).

A maintainer (llvm-beanz) posted a one-line patch to `WriteUtf8ToConsole`
that on Linux/macOS stops round-tripping UTF-8 text through
UTF-8->UTF-32->UTF-8 before printing (bypassing the fallible conversion
entirely), and confirmed in 2024-10-09 that the bug "does still reproduce".

**"This reproduces" is defined as:** running the exact repro command produces
**no** `-fcgl` textual dump on stdout (empty/near-empty stdout with exit 0),
specifically because the pretty-printed module contains a byte sequence that
is not valid UTF-8 (the serialized root signature blob), which makes
`Unicode::UTF8BufferToWideBuffer` fail and the console-writing helper
silently discard the text.

**Repro quality: complete** -- the issue includes the exact command line and
a minimal, complete HLSL shader.

**Platform caveat, stated up front:** this issue is filed and reproduced only
on macOS/Linux consoles (llvm-beanz confirmed on non-Windows). The triage
ground-truth build here is a Windows Debug `dxc.exe`. `lib/DxcSupport/dxcapi.use.cpp`
and `lib/DxcSupport/Unicode.cpp` are compiled for all platforms (the Windows
types are provided cross-platform via `WinAdapter`), and `WriteUtf8ToConsole`
calls the *same* `Unicode::UTF8BufferToWideBuffer` function regardless of
platform, so the underlying conversion-failure logic can, in principle, be
exercised and inspected on Windows too. But the real Win32
`MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, ...)` implementation used
on Windows may reject/accept the same bytes differently than the POSIX
`WinAdapter` shim used on macOS/Linux, so a clean run on Windows does not by
itself prove the macOS defect is fixed, and a failing run on Windows does not
by itself prove the macOS defect persists in its exact reported form -- both
directions need the source-level comparison in `notes.md`, not just the exit
status of one console run.

Given this, the most honest primary verdict is `not-compiler-verifiable` for
the platform-specific console-corruption claim itself, corroborated by:
(1) whether the reported code path (`WriteUtf8ToConsole` /
`UTF8BufferToWideBuffer` / `WriteWideNullTermToConsole`) is unchanged from
what the maintainer described and patched against, and (2) whether the
suggested one-line fix from the thread has been applied to `main` (it has
not, per source inspection at the ground-truth commit) or superseded by any
other locale/console-writing rework mentioned in damyanp's comment.
