> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6005](https://github.com/microsoft/DirectXShaderCompiler/issues/6005).

Still reproduces on `main` (commit `13730886e`) in an assert-enabled Debug build, using the
exact command line and source @s-perron posted above:

```
Error: assert(MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking")
File:
<repo>/tools/clang/lib/Sema/SemaDecl.cpp(11156)
Func:   clang::Sema::ActOnFinishFunctionBody
```

Same assert, file and function @s-perron reported (their build hit line 11119; the ~2-year
drift to 11156 is unrelated `SemaDecl.cpp` edits, not a different assert). Confirmed
independent of `-spirv`: removing it trips the same assert compiling to DXIL. Continuing past
the assert (i.e. running the code path a Release build's compiled-out assert takes) still
produces a well-formed SPIR-V module — consistent with the original report that the shader
compiles despite the assert.

Every stable release from v1.7.2207 onward compiles this cleanly, but that is not evidence of
a fix: all release binaries are Release builds, and `assert()` is compiled out under `NDEBUG`,
so a Release binary structurally cannot show this symptom. The same applies to Compiler
Explorer, which only runs Release builds:
https://godbolt.org/z/h7WEM3v8G (the shared page states this limitation). No older
assert-enabled build was available in this session to check when the assert was introduced.

Releases through v1.6.2112 can't run this particular command at all (`-HV 202x`/HLSL 2021
predates them: `Unknown HLSL version: 202. Valid versions: 2016, 2017, 2018, 2021`) —
unrelated to this bug.

Suggest adding `crash` (assert-only crash, currently missing) and `type-system` (triggered by
a user-namespace typedef whose name collides with the type produced by HLSL's own builtin
`vector<T,N>`/`matrix<T,R,C>` templates).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
