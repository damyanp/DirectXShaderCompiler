> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5117](https://github.com/microsoft/DirectXShaderCompiler/issues/5117).

This still reproduces on `main` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), and it is a bit
worse than described: with `-MD`/`-MF` (or plain `-M`), `dxc` doesn't just fail to print
diagnostics — it reports a **successful compile (exit 0)** for source it would otherwise
correctly reject.

```
$ dxc -T ps_6_0 -E main repro.hlsl
repro.hlsl:3:10: error: use of undeclared identifier 'badIdentifierNotDeclared'
  return badIdentifierNotDeclared;
         ^

$ dxc -T ps_6_0 -E main -MD -MF repro.d repro.hlsl
(exit 0, no output at all)
```

Compiler Explorer, same source, same two invocations: https://godbolt.org/z/s4Mcsxj66

The cause: `-M`/`-MD`/`-MF` all set a single `opts.DumpDependencies` flag
(`lib/DxcSupport/HLSLOptions.cpp`), which routes `DxcContext::Compile` through
`clang::PreprocessOnlyAction` (`tools/clang/tools/dxcompiler/dxcompilerobj.cpp`, the
`DumpDependencies` branch) instead of the normal compile action. That action never constructs a
`Parser` or `Sema`, so no parse- or semantic-level diagnostic is ever produced — there's nothing
for the later `hasErrorOccurred()` check to see. Preprocessor-level errors (e.g. a missing
`#include`) still surface correctly, since the preprocessor *is* what runs in this mode; it's
specifically parser/Sema diagnostics (undeclared identifiers, missing semicolons, etc.) that go
missing. This has been true since dependency dumping was added
(#4017, Dec 2021) — every release that has the flag at all reproduces this.

Given a build could treat this exit code as "the shader is fine," I'd suggest `bug` and
`diagnostic` in addition to the existing `high-impact`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
