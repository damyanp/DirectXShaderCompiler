> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5567](https://github.com/microsoft/DirectXShaderCompiler/issues/5567).

Still reproduces on `main` (main-debug, `89e2f98e2`). `dxc -T cs_6_6 repro.hlsl -Od`
on

```hlsl
[numthreads(1, 1, 1)]
void main()
{
  uint2 a = (1, 2) / 2;
}
```

compiles clean with no `-Wcomma-in-init` diagnostic. The same comma pair with no
division, `uint2 a = (1, 2);`, still gets the warning on the identical build, so the
check itself is intact — it just doesn't look inside `firstArg` for a comma
expression, only at `firstArg` itself
(`SemaHLSL.cpp`, `IsExpressionBinaryComma`/`warn_hlsl_comma_in_init`). That has been
this narrow since before this repository's oldest history is checkable; a 20-release
scan (`v1.4.1907`..`v1.9.2607`, `v1.6.2104` the oldest that supports `cs_6_6`) never
reproduced anything else.

@damyanp's comment above is confirmed on a fresh check: `hlsl_clang_trunk` on
[Compiler Explorer](https://godbolt.org/z/dPM8vnz5b) does flag this shape today,
via `-Wunused-value` ("left operand of comma operator has no effect") rather than a
dedicated `-Wcomma-in-init`-style check — a more general diagnostic that happens to
catch the same mistake.

Suggested: keep `enhancement`, `diagnostic` — this is a real, still-open gap in
`-Wcomma-in-init`'s coverage, not a bug in generated code.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
