> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5961](https://github.com/microsoft/DirectXShaderCompiler/issues/5961).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`). Recompiling the
shader from the linked [Compiler Explorer example](https://godbolt.org/z/9PfEPYa3M) reproduces
the exact warning text quoted in the issue:

```
repro.hlsl:13:19: warning: implicit conversion from 'literal float' to 'int' changes value from 2147483648 to 2147483647 [-Wliteral-conversion]
    store(to_int(-2147483648.0)); // MaxNegative int: -2147483648
```

DXC's own DXIL output for the same compile constant-folds each `to_int`/`to_uint` call and
agrees with the source comments (`-2147483648`, `-2147483648`, `2147483647`, `0`,
`4294967295`), not with the warnings, on exactly the three lines whose literal has an explicit
unary minus. The root cause is in `Sema::AnalyzeImplicitConversions`
(`tools/clang/lib/Sema/SemaChecking.cpp`): when the source expression is a `UnaryOperator`
negating a `FloatingLiteral`, the code strips the minus and hands the **positive** literal to
`DiagnoseFloatingLiteralImpCast`, which then computes and prints both the "from" and "to"
numbers from that positive value — discarding the sign before the warning is even formatted.
Actual codegen evaluates the whole (negated) constant separately and gets it right, which is
why the two disagree only where a unary minus is involved.

This has been present in every stable release DXC has shipped (`bisect --linear`,
v1.4.1907..v1.9.2607, 20 releases, no invalid probes) and in [both CE's oldest DXC (1.6.2112)
and `dxc_trunk`](https://godbolt.org/z/95MndY74x) — it predates the report by several years and
is not something HLSL 202x's conforming-literals changes happen to fix either: retesting with
`-HV 202x` still prints a positive source value for negated literals (verified locally), it is
just wrapped in different-looking numbers because 202x also changes how these literals are
typed.

Labels (`bug`, `tech-debt`, `diagnostic`) still look right; no changes proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
