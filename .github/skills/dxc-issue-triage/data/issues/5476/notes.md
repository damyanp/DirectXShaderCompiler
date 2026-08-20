# Issue #5476 -- "[MacOS only] dxc dump nothing when -fcgl with root signature"

## What was tested

Ground truth: `main-debug`, Windows Debug build, self-reports
`1.9.0.5465 (triage, 7665270b9)`; registered `git_commit` is
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (upstream `main`, verified
`git merge-base --is-ancestor` true against `upstream/main`; see
`.cache/compilers/main-debug.json` `provenance_note` for the local-branch
vs. upstream-tree equivalence check).

Repro (`repro.hlsl`, `cmd.txt`): the exact shader and flags from the issue
body -- a `cs_6_0` compute shader with a `[RootSignature(...)]` attribute on
`main`, compiled with `-fcgl -E main` (repro quality: complete, taken
verbatim from the issue).

1. `python scripts/triage.py run --issue 5476` against `main-debug`
   (`out-main-debug.txt`).
2. `python scripts/triage.py godbolt --issue 5476 --compilers
   "dxc_1_6_2112,dxc_trunk"` against Compiler Explorer's Linux-hosted DXC,
   oldest available (`dxc_1_6_2112`, built 2021-12) and rolling `dxc_trunk`
   (`manual-case-godbolt-verify.txt`, link
   https://godbolt.org/z/vajbo9sxW).
3. Git history search over `lib/DxcSupport/dxcapi.use.cpp`,
   `lib/DxcSupport/Unicode.cpp` and `include/dxc/WinAdapter.h` for changes to
   the console-writing / Unicode-conversion code since the issue was filed.

## Why this cannot be a straightforward `repros` / `does-not-repro`

The reported symptom is **platform-specific**: dxc's console-writing code
path is shared across platforms (`lib/DxcSupport/dxcapi.use.cpp` is compiled
everywhere via the `WinAdapter` shim), but the actual conversion routine it
calls, `Unicode::UTF8BufferToWideBuffer` -> `MultiByteToWideChar`, has a
**real Win32 implementation on Windows** and a **from-scratch emulation on
*nix** (`lib/DxcSupport/Unicode.cpp`, guarded `#ifndef _WIN32`) built on
`mbstowcs()` plus a locale switch (`ScopedLocale`, `include/dxc/WinAdapter.h`).
The bug the reporter and llvm-beanz describe is specific to that *nix
emulation failing (silently) on their machine; it has no Windows analogue
because Windows never runs that code.

Confirmed on `main-debug` (Windows): the repro compiles and prints the
**complete** `-fcgl` dump, including the root-signature bytes as a hex-escaped
`[92 x i8] c"\02\00\00\00...` constant and the `!dx.rootSignature = !{...}`
metadata (`out-main-debug.txt` lines 40-148). Every byte in that printed
constant is either printable ASCII or a backslash-hex escape, so the printed
text is trivially valid UTF-8/ASCII regardless of the actual root-signature
byte values -- Windows was never going to be able to show this bug for this
particular repro, which is exactly what `expected.md`'s platform caveat
predicted before running anything.

**Verdict for the platform-specific claim itself: `not-compiler-verifiable`.**
No compiler in this triage's toolkit runs on a system that can exhibit the
failure:

- `main-debug` is a native Windows build (real Win32 `MultiByteToWideChar`,
  no locale dependency) -- clean by construction, proves nothing about macOS.
- Compiler Explorer's DXC panes *do* run on Linux, which does exercise the
  *nix emulation path in principle. Both `dxc_1_6_2112` (2021-12, four years
  before the candidate fix below) and `dxc_trunk` compiled the repro cleanly
  and printed the complete dump (`manual-case-godbolt-verify.txt`, both
  panes `# exit: 0`, both containing `!dx.rootSignature = !{!90}`). Since
  even the *oldest* CE build -- long predating any fix -- does not reproduce
  the failure, this is a **matching-clean-endpoints trap in exactly the shape
  the skill warns about**: CE's Linux build environment evidently always has
  a working UTF-8 locale available to `mbstowcs`/`setlocale`, so it can never
  show this failure regardless of whether the underlying code is buggy or
  fixed. A clean CE pane here is a property of CE's own environment, not
  evidence about the reporter's or llvm-beanz's machine, and **does not
  corroborate a fix boundary** -- there is no boundary to find with an
  instrument that was never able to detect the symptom in the first place.

## A concrete, highly plausible (but unconfirmed) fix candidate

`git log --oneline -- lib/DxcSupport/Unicode.cpp` shows exactly one
functionally-relevant change since the issue was filed:

commit `9bcce409bd46ac5736c166252fbafd4754c51a55` ("Fix potential unicode
conversion issues for *nix (#7506)", merged 2025-11-25, author Tex Riddell) --
confirmed an ancestor of ground truth
(`git merge-base --is-ancestor 9bcce409b 89e2f98e29c` -> true). The only
later touch to that file, `9a2ee990641` ("Include <new> in Unicode.cpp
(#8078)", 2026-01-23), is a missing-`#include` fix with no logic change
(`git show --stat` -- 1 file, 1 insertion).

This commit rewrites exactly the code the issue and llvm-beanz's comment
describe:

- `ScopedLocale` (`include/dxc/WinAdapter.h`) previously called
  `setlocale(LC_ALL, "en_US.UTF-8")` -- a **process-global, not thread-local**
  locale change -- with **no check that it succeeded** (`setlocale` returns
  `nullptr` on failure and the C library silently keeps whatever locale was
  already active). It now uses `newlocale`/`uselocale`, which is per-thread,
  asserts if no UTF-8 locale name resolves, and restores the previous
  thread-local locale on scope exit.
- `MultiByteToWideChar`'s *nix emulation (`lib/DxcSupport/Unicode.cpp`) is
  rewritten to reject invalid sizes up front, fix an off-by-one in the
  null-terminator accounting, and -- most relevantly -- explicitly detect and
  report an `mbstowcs` failure (`rv == (size_t)-1`) instead of relying on the
  return-value arithmetic to happen to fall through to 0.
- The commit message states directly: "There were multiple issues with
  Unicode conversion on *nix platforms. This PR fixes issues I found with the
  conversion functions that were causing failures when running locally, due
  to issues with setting the locale."

This is precisely the failure class the issue reports (a *nix-only,
locale-dependent, silent Unicode-conversion failure in the console-writing
path), landed as a single well-scoped fix between llvm-beanz's 2024-10-09
"this does still reproduce" comment and this triage's ground truth. **I could
not verify it directly**, because:

- Nothing in the PR body, commit message, or the issue's own GitHub timeline
  cross-references #5476 (`gh api .../issues/5476/timeline` shows exactly one
  pre-existing cross-reference, to unrelated PR #5472, a matrix-test change).
- Reproducing the *exact* reported failure requires a *nix machine (or
  container) whose `setlocale(LC_ALL, "en_US.UTF-8")` genuinely fails or
  raced under the old code -- this environment has no WSL distribution and no
  container runtime available (`wsl --status` reports no installed
  distributions; `docker` is not on `PATH`), and installing one was judged
  out of scope for a single-issue triage rather than attempted.
- Compiler Explorer's Linux environment, the one *nix system this triage
  could reach, never manifested the symptom on either side of the fix (see
  above), so it cannot corroborate or refute the attribution either way.

**Confidence: medium, not high.** The source match to the reported failure
class is strong and the timing is exactly right, but this is a source-level
inference, not a reproduced-and-confirmed-fixed measurement, and per the
skill's own guidance a plausible-looking match to a bug's description is not
the same as building at the commit and testing it.

## What the fix in the thread did *not* land

llvm-beanz's 2023-08-01 patch (posted in a comment) took a different
approach: bypass the UTF-8->wide->UTF-8 round trip on Linux/macOS entirely by
writing UTF-8 text straight to `stdout`/`stderr` with `fprintf`. That patch
was never applied to `main` (current `dxcapi.use.cpp::WriteUtf8ToConsole`
still round-trips unconditionally through
`Unicode::UTF8BufferToWideBuffer(...)` -> `WriteWideNullTermToConsole(...)`
on every platform, unchanged in shape since the issue was filed). The actual
landed fix (PR #7506) addresses the same underlying defect from the other
side: instead of skipping the fallible conversion, it repairs the conversion
and its locale handling. Worth noting in case a reader assumes the posted
diff is what shipped -- it is not.

## Labels

Current: `bug`, `macos`, `usability`. All three remain accurate: this is
still an unresolved-by-confirmation, macOS-specific usability defect
(silent tool failure, no diagnostic). No label change proposed.

## Text staleness

None. The issue body and comments still accurately describe the reported
behavior and its history; nothing in the thread is contradicted by what
could be measured here.
