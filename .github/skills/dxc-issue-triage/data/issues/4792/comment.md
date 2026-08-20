> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4792](https://github.com/microsoft/DirectXShaderCompiler/issues/4792).

Still reproduces on `main` (verified against a Debug build at
89e2f98e29c289ae8ad9e00dd310104fea9fd7df) — not because a hang was reproduced in this
session, but because the racy code you found is unchanged:

```
$ git log --oneline --all -- include/llvm/PassSupport.h
f805233b4 Revert license text in banner comments to original llvm verbage (#33)
6ee4074a4 first commit
```

`CALL_ONCE_INITIALIZATION` has never been touched since the repo's first commit. #4818, which
would have applied the `static`-initializer fix from D19271 you mentioned, is still closed
and unmerged.

Worth reading the full #4818 thread if you haven't: after that PR opened, @llvm-beanz talked
through it with you in real time, and by the end of it your `std::call_once` port had *also*
locked up — this time inside libstdc++'s `__cxa_guard_acquire`, on a different pass
(`TargetTransformInfoWrapperPass`) — and a ThreadSanitizer run on DXC turned up several
unrelated data races (`ManagedStatic`, `MutexImpl::acquire`, `Sema`'s implicit special-member
declaration, one heap-use-after-free). Nobody in that thread claims the concurrency problem
was actually solved; it reads like it was still open when the PR was closed for inactivity.

I built a small multithreaded harness that loads `dxcompiler.dll` and fires many threads at
`IDxcCompiler3::Compile` from a shared barrier, to try to reproduce the hang directly. Across
13 attempts (8 through 512 threads, up to 512 all racing the same cold-start compile at once),
it did not hang on this Windows/MSVC Debug build. That's a bounded negative result on one
platform, not a "fixed" — your two stack traces are both inside Linux/glibc-specific
primitives (`__gthread_once`, `__cxa_guard_acquire`) with no direct Windows equivalent in this
call path, so a clean Windows run doesn't say much about the Linux behavior you and
@llvm-beanz were chasing.

Given the source is unchanged and the fix discussion stalled without a resolution, this looks
like it should stay open rather than close. Adding `bug` and `api` labels since there
currently are none on the issue.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
