# Notes -- #4792 `libdxcompiler.so` locks up when used in many threads at once

## Summary

The reporter observed `libdxcompiler.so` hanging on Linux when many threads call the compiler
concurrently, and traced it to `CALL_ONCE_INITIALIZATION` in `include/llvm/PassSupport.h` --
a hand-rolled double-checked-locking pattern (`static volatile` flag + `CompareAndSwap` +
`MemoryFence()`) guarding lazy, first-use registration of each LLVM legacy pass
(`llvm::initializeLoopSimplifyPass` and friends), reached from `addHLSLPasses` while building
the backend pass pipeline for the first compile in a process. A PR that would have replaced
the mechanism with a `static`-initialized-lambda variant
(https://reviews.llvm.org/D19271, matching what the issue body says the reporter was running
without further lockups) was opened as microsoft/DirectXShaderCompiler#4818, "Fixes #4792" --
and was **closed unmerged** by a maintainer as part of an inactivity sweep, roughly a year
after the reporter said they were still shipping the patch downstream because they had no
merge permission of their own.

## Source-level finding (verified, durable)

```
git log --oneline --all -- include/llvm/PassSupport.h
f805233b4 Revert license text in banner comments to original llvm verbage (#33)
6ee4074a4 first commit
```

`include/llvm/PassSupport.h` has **never been modified** since the repository's first commit
(only a license-banner revert touched it). The exact `CALL_ONCE_INITIALIZATION` macro the
issue quotes is byte-for-byte what is on `main` today (lines 36-54). No fix has landed. This
by itself, independent of any dynamic reproduction, establishes that the reported defect is
still present in source and the discussed remediation was abandoned rather than resolved.

`sys::MemoryFence()`/`sys::CompareAndSwap()` (`lib/Support/Atomic.cpp`) are implemented on
every supported platform (`__sync_synchronize`/`__sync_val_compare_and_swap` on GNU/GCC,
`MemoryBarrier`/`InterlockedCompareExchange` on MSVC) -- the racy pattern is genuinely
cross-platform code, not Linux-only, even though the reporter's own repro happened on Linux.

## PR #4818 discussion (read via `gh pr view --comments`)

The linked, closed PR's comment thread is itself important context: it shows a DXC maintainer
(`llvm-beanz`) and the reporter iterating on **three different** fixes in real time --
1. the reporter's initial forward-port to `std::call_once` (still hung, `__gthread_once`)
2. a `static std::once_flag` + lambda variant suggested in the PR thread (which the maintainer
   also expected to work)
3. building with `-DLLVM_USE_SANITIZER=Thread` to look for the root cause

-- and that **variant 2 also locked up** for the reporter, this time inside libstdc++'s
`__cxa_guard_acquire` (a *different* synchronization primitive than either `CALL_ONCE_INITIALIZATION`
or `std::call_once`), on a shader compile going through `TargetTransformInfoWrapperPass`
rather than `LoopSimplify`. ThreadSanitizer output attached to the PR (before the DXC-only
run was later found to have been built without TSan and its output deleted) still reported
races elsewhere: `ManagedStatic::operator*()`, `MutexImpl::acquire()`,
`raw_fd_ostream::preferred_buffer_size()`, `Unicode.cpp`'s `WideCharToMultiByte`, and several
`clang::Sema` "declare implicit special member" paths, plus one heap-use-after-free in
`char_traits<char>::copy`. This is why the maintainer's own words on the thread are: "I don't
think we should use `llvm::call_once` either... If gthread_once is locking up on modern
implementations that's... terrifying" and "That's fun... I wish I could say I'm surprised".
**No party in that thread claims the underlying concurrency problem was solved**; the PR was
closed for inactivity, not because the fix landed some other way -- confirmed with
`git log --all --grep` finding no commit referencing `4818` or `D19271`, and the unchanged
file history above.

## Dynamic probe: multithreaded harness against `main-debug`

Because the symptom only appears when many threads call the *same loaded compiler instance*
concurrently, it is not something a single `dxc` CLI invocation (or `triage.py bisect`, which
drives one `dxc.exe` process per probe) can exercise. `cmd.txt`/`match.json` in this directory
are a **sanity control only** -- they confirm `repro.hlsl` (a trivial `[numthreads(1,1,1)]`
compute shader) compiles cleanly single-threaded on `main-debug`, exercising the same
`addHLSLPasses` backend path the issue's stack trace names (`out-main-debug.txt`).

`mt-harness.cpp` (this directory) is a small Win32 program that:
- `LoadLibrary`s `dxcompiler.dll` directly (mirroring a consumer dlopen'ing
  `libdxcompiler.so`, as the reporter's build system does) and resolves `DxcCreateInstance`
  by name;
- spawns N worker threads, each of which creates its **own** `IDxcCompiler3` instance and
  waits on a shared manual-reset event (a barrier);
- releases every thread from the barrier simultaneously, so the very first `Compile()` call
  from every thread races to cold-start pass registration together -- the scenario in the
  issue's own stack trace, reached at process start before any pass's
  `CALL_ONCE_INITIALIZATION` flag has been set;
- polls each thread's completion via an `std::atomic<bool>` per thread rather than
  `WaitForMultipleObjects` -- see `method-notes.md`, that API caps out at 64 handles and
  silently returned `WAIT_FAILED` on this Windows host once `numThreads > 64`, which the
  first cut of this harness did not check for and read as a false, near-instant "clean" run;
- on a bounded timeout with any thread still not done, suspends every unfinished thread,
  resolves its instruction pointer against `dxcompiler.dll`'s loaded base+size via
  `GetModuleInformation`, prints `dxcompiler.dll+0x<offset>` per stuck thread, and terminates
  the process with exit code 124 (chosen to read like the project's own `timeout` convention).

`gen-mt-harness-capture.py` runs the harness at a fixed, disclosed schedule (8, 16, 32, 64, 96,
128 threads once each, 256 threads x4, 512 threads x3 -- 13 attempts total) and writes the full
transcript, including the exact argv for every attempt, to `manual-case-mt-harness.txt`.

**Result: 0/13 attempts hung**, up to 512 concurrent threads, all racing the same cold-start
compile simultaneously on this Windows 11 / MSVC / Debug `main-debug` build. Every attempt
finished in well under the timeout (worst case ~2.5s at 512 threads) and every thread's
`Compile()` call succeeded.

**This does not mean the source-level defect is fixed** (the file is byte-for-byte unchanged,
above), and it is not read as `does-not-repro`. Two things plausibly explain a clean Windows
result without contradicting the Linux report: (1) the reporter's own two failing stack traces
are both firmly inside Linux/glibc primitives with no Windows equivalent in this call path --
`__gthread_once`/libstdc++'s `mutex` implementation for the `std::call_once` variant, and
`__cxa_guard_acquire` (the Itanium-ABI thread-safe-static-init guard) for the
`static`-initializer variant the PR discussion moved to next -- while MSVC's function-local
static initialization and `InterlockedCompareExchange`/`MemoryBarrier` are a different,
independently-implemented mechanism; and (2) the reporter's own matrix reports the hang rate
as "before reaching 10" runs of a **64-way parallel full asset-build pipeline** on a real
32-core/64-thread machine, not a single cold compile call repeated in a tight loop on this
VM's hardware -- the timing window may simply need more concurrent contention or a different
scheduler than this host provides. Neither point is verified here; both are stated as
explanations for the discrepancy, not established causes. The finding that should be trusted
is the source one: the racy code is unchanged and the fix attempt was abandoned, not that
Windows Debug is somehow immune.

## Verdict

- **status**: `repros` -- read as "the reported defect (the racy, unfixed pass-registration
  synchronization) is still present", per source evidence, not because this session observed
  a hang.
- **repro-quality**: `agent-constructed` -- no HLSL shader repro was ever needed or given; the
  harness and trivial compute shader used here were built for this triage.
- **history**: effectively `always-repro'd` at the source level: `include/llvm/PassSupport.h`
  has been unchanged since the repository's first commit, and the one PR that would have
  changed it was closed unmerged.
- **confidence**: high for the source/PR-history claim (durable, git- and `gh`-verified);
  low/unmeasured for "still hangs today under real-world contention", which this session's
  bounded Windows probe could not confirm or refute one way or the other.
- **not-compiler-verifiable** would understate this -- the source claim *is* compiler/repo
  verifiable and was verified; only the live-hang claim is unmeasured here.
- **suggested-action**: `still-valid-keep-open`. The maintainer's own read of the situation in
  the PR thread ("that's... terrifying", no resolution offered) plus the unmerged fix and
  wider TSan findings argue this needs real engineering attention (ideally with
  ThreadSanitizer, which the maintainer already got building for DXC in that thread), not a
  close.
- **text-stale**: none. The issue title and body still accurately describe both the symptom
  and the currently-unfixed code.

## What this triage could not determine

- Whether the hang still reproduces on Linux/glibc as originally reported -- this session had
  only a Windows host and the registered `main-debug` compiler is a Windows Debug build.
- Whether a higher thread count, different shader (more/different lazily-initialized passes),
  or longer sustained load would eventually reproduce a hang on Windows too. The 13 attempts
  captured here are a bounded negative result, not a proof of absence.
- Root cause beyond what is already stated in the PR thread. A plausible, unverified
  hypothesis (mine, not sourced) is a lock-ordering (AB-BA style) deadlock across two passes
  whose `INITIALIZE_PASS_DEPENDENCY` chains are reached in opposite orders by two different
  threads, which would explain why three independently-implemented once-only mechanisms (the
  original CAS+fence macro, `std::call_once`, and the static-lambda initializer) all showed
  similar failure shapes in the reporter's own testing except the last one in limited runs;
  this was not verified against the dependency graph and must not be quoted as established.
