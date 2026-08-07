# Expected symptom - #3686 Binary release artifacts for macOS

Written **before** gathering any evidence, from the issue text and its 12 comments alone.

**Repro quality: `prose-only`, and necessarily so.** This is not a compiler defect. There is no
shader, no command line and no compiler output that could show it. The issue asks a question
about **what the project publishes as release artifacts**, so the compiler under test cannot
answer it: a perfectly working `dxc` binary that is never uploaded to a release is exactly the
situation being reported. Running the ground-truth build here would measure nothing.

Expected verdict class: `not-compiler-verifiable`. Forcing `repros` / `does-not-repro` would
be a category error - "reproducing" a missing download is not an operation the tooling has.

## What the issue actually asks, after its retitle

Filed 2021-04-14 by @kvark as *"Would it be possible to include the Linux/macOS builds in the
releases?"*. On 2023-07-08 @llvm-beanz wrote *"We have shipped Linux binaries, and I've
re-titled to track macOS"* - so the live scope is **macOS only**, and the Linux half is
claimed already delivered. Both halves are checkable.

## What "this is still an open gap" would mean, precisely

All three must hold. Each is a fact about published artifacts and repo configuration, not
about compiler behaviour:

1. **No published release of `microsoft/DirectXShaderCompiler` carries a macOS binary asset.**
   Not the newest one only - the whole release list, so that "when did this change" can be
   answered rather than assumed. A macOS asset would be named for Darwin/macOS/osx or be a
   `.dmg`/`.pkg`, or a universal/arm64 archive.
2. **The repo's own CI/release configuration does not build or publish a macOS artifact.** If
   a macOS job exists but its output is never uploaded to a release, that is a *different*
   finding and must be reported as such.
3. **No maintainer statement in the thread has been superseded.** @llvm-beanz's 2025-10-15
   comment says there are *no plans* for macOS releases, blocked on code signing. If that is
   the project's current position, the issue is not stale - it is answered-and-declined, which
   is a decision, not a measurement.

Conversely, **"the gap is closed"** would require finding a macOS binary attached to an
actual GitHub release of this repo. Anything less is not that.

## Three claims that must not be conflated

The issue asks about the **first** only. Evidence for the second or third is not evidence for
the first, and the thread itself repeatedly slides between them:

| claim | who says it | what it would take to check |
| --- | --- | --- |
| **macOS binaries are published by this project** | what the issue asks for | a macOS asset on a `microsoft/DirectXShaderCompiler` release |
| macOS is **buildable from source** | @pow2clk c3: *"It's there for whomever wants to build it"* | CMake/platform support in-tree |
| **someone else** publishes macOS builds | @kuhar c5 (Vulkan SDK / LunarG), @ThomasFOG c11 (MonoGame) | third-party, and @llvm-beanz c12 explicitly advises against relying on it |

## Subsidiary claims worth checking while there

- **Linux was delivered** (c7, 2023-07-08). Which release first carried a Linux asset? That
  dates the half that *was* done and is the strongest available evidence that the remaining
  half is genuinely still open rather than merely unrecorded.
- **DXIL signing/hashing is now in-tree** (@damyanp c9 pointing at #6770; @llvm-beanz c12
  *"DXIL hashing is included in the public DXC sources"*). Several commenters give the missing
  signing DLL as the blocker; if that blocker is gone, the *stated* remaining blocker has
  changed - from DXIL signing to Apple code signing - and the thread's older comments read
  stale.

## Out of scope

Whether Microsoft *should* ship macOS binaries. That is a resourcing and platform-policy
decision, already stated by a maintainer, and triage has no standing to re-open or re-litigate
it. The job here is to establish whether the facts underneath the decision still hold.

## Compiler Explorer

Expected to be skipped. There is no source to compile: a link showing a shader building fine
would say nothing about what a release ships, and would actively mislead.
