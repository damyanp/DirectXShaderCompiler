> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4615](https://github.com/microsoft/DirectXShaderCompiler/issues/4615).

Still current on `main` (1.9.0.5433, `13730886e`). With one statement before
and one after `#line 400 "virtual-source.hlsl"`, DXIL debug metadata keeps the
physical file and lines:

```llvm
!1  = !DIFile(filename: "repro.hlsl", directory: "")
!68 = !DILocation(line: 7, column: 10, scope: !4)
!69 = !DILocation(line: 9, column: 17, scope: !4)
```

The measured boundary is v1.5.2010, not version 1.6: v1.4.1907 emits
`!DILocation(line: 400)` and `!DIFile(filename: "virtual-source.hlsl")`;
all 19 later stable releases use physical locations.

The boundary and source history strongly support the issue's attribution to
PR #2991 (`bce85df11`). That commit lies between those two releases, changed
the `getPresumedLoc` calls to pass `UseLineDirectives=false`, and added
`pound_line.hlsl`, which tests the current behaviour.

The compiler still treats other consumers differently. A diagnostic after the
directive reports:

```
virtual-source.hlsl:400:17: error: invalid format for vector swizzle 'no_such_member'
```

and `-spirv -fspv-debug=line` emits `OpLine` for virtual line 400. No opt-in
flag exists for DXIL debug locations. `-ignore-line-directives` goes the other
way, making diagnostics physical too; `-line-directive` is rewriter-only.

[Compiler Explorer](https://godbolt.org/z/fdMjWcKd1) shows the DXIL/SPIR-V
contrast and that `hlsl_clang_trunk` already emits the virtual location. CE's
banner shifts physical lines 7 and 9 to 31 and 33; that is not a compiler
difference.

Suggested labels: `debug info` and `enhancement`. The remaining request is an
opt-in flag, so `enhancement-not-bug` remains the recommended disposition.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
