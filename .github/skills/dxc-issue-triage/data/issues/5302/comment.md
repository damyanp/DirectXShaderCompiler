> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5302](https://github.com/microsoft/DirectXShaderCompiler/issues/5302).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).

Byte-for-byte identical to the IR quoted in the issue:
`-T ps_6_0` keeps the buffer load inside the loop, guarded by `dx.break`; `-T vs_6_0` on the
*same source* hoists it out, with no `dx.break` anywhere in the output.

@simondeschenes's diagnosis is right: `CGMSHLSLRuntime::EmitHLSLCondBreak`
(`tools/clang/lib/CodeGen/CGHLSLMS.cpp`) only conditionalizes the break for `IsPS()`,
`IsCS()` and `IsLib()`. Every other stage falls through to a plain unconditional branch, so
the protection PR #2795 added never applies there. That guard is unchanged since PR #2795
introduced it on 2020-03-30 (`d3af7f123`).

History: reproduces on every stable release from v1.5.2010 (the first release to ship
`dx.break`) through v1.9.2607, and on `main-debug`. v1.4.1907 predates PR #2795, so neither
`vs_6_0` nor `ps_6_0` shows `dx.break` there; that's the mechanism being absent for every
stage, not evidence the bug wasn't happening yet.

Compiler Explorer, `vs_6_0` vs `ps_6_0` on two DXC versions: https://godbolt.org/z/jj8fzqMTK

Suggesting `correctness` and `incorrect-code` in addition to `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
