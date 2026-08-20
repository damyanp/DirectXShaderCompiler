> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4965](https://github.com/microsoft/DirectXShaderCompiler/issues/4965).

This no longer reproduces on `main` (built at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).
Compiling the filed source with `-T ps_6_2 -E f` now gives a clean diagnostic instead of any
internal failure:

```
repro.hlsl:1:1: error: recursive functions are not allowed: function 'f' calls recursive function 'f'
repro.hlsl:1:1: note: recursive function located here:
```

`-E f` makes `f` the entry point, and the source also calls `f` at global scope to initialize
`static int b`. DXC synthesizes calls to global initializers inside the entry-point wrapper it
builds for `f`, so `f`'s own wrapper ends up calling `f` — a genuine self-recursion introduced
by entry-point lowering. The existing recursion check now catches that before codegen runs,
which is why the Debug-build SROA assert reported in this thread
(`otherwise we flattened a library function.`) no longer fires: the compile never reaches that
pass.

A stable-release bisection puts the fix at **v1.8.2505** (last reproducing release: v1.8.2502).
Every stable release from v1.4.1907 through v1.8.2502 does fail internally, matching all of the
symptoms reported in this thread across that time span — a silent access violation, a printed
`Internal compiler error: access violation`, and the `llvm::cast<X>() argument of incompatible
type!` message — depending on release and build configuration. The window between v1.8.2502
and v1.8.2505 is 162 commits; no individual fixing commit was identified.

[Compiler Explorer](https://godbolt.org/z/ee6xoP8jz): CE's oldest DXC (`1.6.2112`, Linux
Release) terminates with `SIGSEGV`, and `dxc_trunk` shows the same diagnostic as above —
corroborating both the old crash and the current fix on a second platform.

Suggested labels: add `crash` (this was a crash/assert issue for its whole open lifetime,
which the current label set doesn't capture); no other changes.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
