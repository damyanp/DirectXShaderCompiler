# Expected symptom — #4792

## What the reporter says

`libdxcompiler.so` (Linux shared library) hangs/deadlocks when many threads concurrently
invoke the compiler (e.g. a parallel shader-asset build spawning dozens of compile jobs
against the same loaded `libdxcompiler.so`). Repeated over ~10-20 runs of a build with 64
parallel jobs, it eventually hangs.

Two distinct hangs are reported, both inside LLVM pass-registration machinery reached via
`addHLSLPasses` -> `PMTopLevelManager::schedulePass` -> `llvm::callDefaultCtor<LoopSimplify>`
-> `llvm::initializeLoopSimplifyPass`:

1. **Original code** (`CALL_ONCE_INITIALIZATION` macro in
   `include/llvm/PassSupport.h`, a hand-rolled double-checked-locking pattern over a
   `static volatile` flag plus `llvm::sys::MemoryFence()`): many threads sit forever inside
   `MemoryFence()` or inside `initializeLoopSimplifyPass` itself.
2. **Reporter's own forward-port to `std::call_once`** (an unmerged branch, not present on
   `main`): threads instead sit forever inside libstdc++'s `__gthread_once` /
   `std::call_once` for the *same* flag (`InitializeLoopSimplifyPassFlag`). This still hangs.

The reporter says a **third**, different patch — replacing the whole once-mechanism with a
`static` function-local variable initialized via a lambda (the pattern from
https://reviews.llvm.org/D19271, not yet applied upstream) — has not reproduced the hang in
their testing.

The issue includes an internal matrix (comment) contrasting `Release` vs `RelWithDebInfo`
builds and the three patch variants, run 64-wide on a ThreadRipper 3970X, ~10-20 runs each.
Only the `static`-lambda variant survived without a lockup in their environment; `Release`
(the shipped configuration, using the original `CALL_ONCE_INITIALIZATION` macro) failed
"typically ... before reaching 10" runs.

## What "reproduces" means here

The reported defect is in code that ships on **every platform** — `CALL_ONCE_INITIALIZATION`
in `include/llvm/PassSupport.h` is not `#ifdef`'d per-OS — so if the macro is unchanged on
`main`, the defect is present in source regardless of whether this particular Windows/Debug
environment can be driven into the hang in a reasonable amount of wall-clock time. A
compiler-verifiable claim here has two independent parts:

1. **Source-level**: is `CALL_ONCE_INITIALIZATION` (or equivalent thread-unsafe pass-registry
   initialization) still present on `main`, unchanged from what the reporter examined at
   `24ca1f498`, or has it been replaced (e.g. by the linked D19271-style fix, or by
   `std::call_once`, or by eager/single-threaded registration)?
2. **Dynamic**: can a concurrent multi-threaded harness that repeatedly invokes the compiler
   API (`IDxcCompiler3`/equivalent) from many threads against a fresh `PassRegistry` cold-start
   path be driven to hang or deadlock, within a bounded timeout, on this build?

Because the *original* hang is timing/thread-scheduling dependent (the reporter needed up to
~20 repeated runs of a 64-way parallel build to trigger it even on Linux), a **single clean
run proves very little**; only a hang (or a bounded number of repeated clean runs against a
non-trivial thread count) is informative, and this is `not-compiler-verifiable` for a tight
bound on "never hangs" — it is compiler-verifiable for "the racy pattern is present/absent in
source" and for "a hang can/cannot be produced within N attempts here".

## Repro quality

`prose-only` for a literal, byte-for-byte HLSL repro (none is given — the hang doesn't depend
on shader content, only on concurrent invocation), but the reporter names the exact function
and macro. Treat this as `agent-constructed`: build a multithreaded harness that calls the
registered `main-debug` compiler API from many threads concurrently and drive pass
registration cold each time.

## Failure classification

- `repros` if source still contains the racy `CALL_ONCE_INITIALIZATION` pattern (or an
  equivalent that a source reading shows is not safe against concurrent first-use across
  threads) **and/or** the harness can be driven to hang/deadlock within a bounded timeout.
- `does-not-repro` if `main` has replaced the mechanism with something demonstrably safe
  (e.g. C++11 function-local static, which is thread-safe by the standard) **and** repeated
  concurrent harness runs do not hang.
- `not-compiler-verifiable` for any claim beyond what the harness can bound (e.g. "will never
  hang under any thread count / scheduler" is not something a bounded number of runs proves).
