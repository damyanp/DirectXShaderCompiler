# Method notes -- #4792

Observations about the *method*, for collation to consider promoting. Nothing here changes
the verdict; it is about the tooling used to reach it.

## `WaitForMultipleObjects` silently caps at 64 handles, and treating its return value as a
## boolean "did we time out" hid a false-positive "clean" run

The first version of `mt-harness.cpp` used
`WaitForMultipleObjects(numThreads, handles.data(), TRUE, timeoutMs)` and branched only on
`wait == WAIT_TIMEOUT`. Win32 defines `MAXIMUM_WAIT_OBJECTS == 64`; calling it with more
handles fails immediately with `WAIT_FAILED` (`GetLastError() == ERROR_INVALID_PARAMETER`),
which is neither `WAIT_TIMEOUT` nor a success code. The harness's `else` branch treated
*anything that isn't WAIT_TIMEOUT* as "all threads finished", so at `numThreads=96` it read
`ctxs[i].compileOk` for every thread **before any of them had actually run**, printed a
plausible-looking `CLEAN in 24 ms: threads=96 ok=0 failed-compile=96`, and moved on. This is
the same shape of failure the skill's `invalid-probe` guidance warns about for `dxc.exe`
itself (a probe that never really ran scoring as a confident, wrong-flavoured result) -- it
just shows up one layer down, in a hand-written harness's own wait primitive rather than in
the compiler being probed. A harness that fans out past 64 concurrent units and waits on
native handles needs either batched waits or (what this harness now does) polling a
per-thread atomic flag instead of relying on a single OS wait call. Worth generalizing:
**any custom multithreaded harness that scales past small thread counts on Windows needs to
know about the 64-handle wait ceiling**, and its return value must be checked for both
`WAIT_TIMEOUT` and `WAIT_FAILED`/other unexpected codes rather than assumed to be exactly two
possible outcomes.

## A concurrency defect can be source-verifiable (durable) while being dynamically unmeasured
## on the available host, and the two should be reported as separate confidence levels

This issue's central claim -- "the racy pass-registration code is still on `main` and its one
proposed fix was abandoned" -- is fully verifiable from `git log` and `gh pr view` alone, with
high confidence, no compiler execution required. The claim "and it still hangs in practice" is
a live concurrency race that this session's harness could not trigger in 13 bounded attempts
up to 512 threads on the one available (Windows Debug, MSVC) host, even though the original
reports are Linux/glibc and involve at least two different C++-runtime synchronization
primitives (`__gthread_once`, `__cxa_guard_acquire`) that have no Windows equivalent in this
call path. Collapsing these two into one verdict field would either overclaim ("repros,
confirmed hanging") or underclaim ("does-not-repro" from a clean bounded probe that never had
a chance of exercising the platform-specific mechanism the reporter hit). Recording them
separately in `notes.md` -- source claim vs. dynamic claim, each with its own confidence --
seems like the right shape for any future "known racy code, unmerged fix, platform-specific
manifestation" issue, and might be worth a line in SKILL.md if collation sees the pattern
again elsewhere (this is only one issue's occurrence, so left here rather than promoted).
