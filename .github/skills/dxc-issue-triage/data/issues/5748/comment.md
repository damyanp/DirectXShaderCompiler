> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5748](https://github.com/microsoft/DirectXShaderCompiler/issues/5748).

This no longer reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).
Compiling the repro as a library target (`-T lib_6_3`, and separately re-checked at the
originally-filed `-T lib_6_5`) now correctly fails validation:

```
error: validation errors
<source>:47:16: error: Thread Group Shared Memory not supported from non-compute entry points.
note: at '%1 = load float, float addrspace(3)* @"...gs.0", align 4' in block '#0' of
function '?HSPatch@@YA?AUPCStruct@@...'.
```

The diagnostic names the patch-constant function (`HSPatch`) directly, not just the
`[shader("hull")]` entry point -- confirming the validator's library-target path now visits
patch-constant functions.

A release-binary bisection across the full stable-release catalog puts the fix at
**v1.9.2607**: every stable release from v1.4.1907 through v1.9.2602.24 still reproduces the
bug (library target validates cleanly despite the groupshared read), and v1.9.2607 onward does
not.

Comparison on Compiler Explorer (CE's oldest DXC vs. current trunk):
https://godbolt.org/z/daqY8a3x8

PR #5749 (opened by this issue's reporter, same day, `Fixes #5748`) proposed a fix but was
never merged -- it was closed unmerged by an inactivity sweep after two years. The measured
release transition indicates this issue was fixed instead as an incidental effect of PR #8140
("Add GroupSharedLimit attribute support for Mesh, Amp and Node shaders"), which changed the
same library-target validation loop to also visit patch-constant functions and added a
regression test. That PR's merge date is earlier than the release that first ships the fix,
so the exact commit-to-release mapping isn't fully pinned down, but the release-binary
transition itself (v1.9.2602.24 -> v1.9.2607) is a direct measurement, not an inference.

Suggest closing as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
