> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5476](https://github.com/microsoft/DirectXShaderCompiler/issues/5476).

Tested against `main` at `13730886e` (2026-08-12): the reported symptom is
platform-specific and could not be directly re-confirmed or refuted, but a
plausible fix candidate has landed since llvm-beanz's last "still reproduces" comment.

**Why this can't be re-confirmed directly.** The bug is in the *nix-only
emulation of `MultiByteToWideChar` (`lib/DxcSupport/Unicode.cpp`), which
Windows never runs (Windows uses the real Win32 API). On Windows, the exact
repro compiles cleanly and prints the complete `-fcgl` dump, including the
root signature bytes — expected, and not evidence either way. Compiler
Explorer's Linux-hosted DXC *does* run the *nix code path, but both the
oldest available build (`dxc_1_6_2112`, Dec 2021) and current `dxc_trunk`
also print the complete dump cleanly
([godbolt](https://godbolt.org/z/vajbo9sxW)) — including on the four-year-old
build that clearly predates any fix. That means CE's own environment never
had the failing locale condition to begin with, so it can't corroborate a
fix boundary here either.

**A plausible fix candidate.** `9bcce409b` ("Fix potential unicode conversion issues for
*nix", #7506, merged 2025-11-25) rewrites exactly this code: `ScopedLocale`
used to call `setlocale(LC_ALL, "en_US.UTF-8")` process-globally with no
check that it succeeded, and the *nix `MultiByteToWideChar` emulation had no
explicit handling for an `mbstowcs` failure. The commit switches to
thread-local `uselocale`/`newlocale` and adds explicit failure detection —
the exact class of "silent Unicode conversion failure on *nix" this issue
describes. It isn't referenced by this issue anywhere, so the connection is
inferred from the code and the timing, not confirmed by testing on an
affected machine (none was available for this triage).

Note: the workaround patch posted in this thread (skip the UTF-8 round trip
on Linux/macOS) was never merged; `WriteUtf8ToConsole` still round-trips
through `UTF8BufferToWideBuffer` on every platform. The fix, if it is one,
came from repairing that conversion rather than bypassing it.

Suggest keeping this open with `bug`, `macos`, `usability` (all still
accurate) until someone can rebuild and test on macOS/Linux against a
compiler containing `9bcce409b` — that's the missing confirmation.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
