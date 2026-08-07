> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3708](https://github.com/microsoft/DirectXShaderCompiler/issues/3708).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`) and all 20 measured
releases from v1.4.1907 through v1.9.2607:

```
repro.hlsl:6:14: error: variable length arrays are not supported in HLSL
    int array[(10).x];
             ^
```

Tested component expressions also fail as enumerators, case labels, non-type
template arguments, bitfield widths, global initializers and `[numthreads]`
arguments:

```
enum E { A = v2.x };
             ^~~~ error: expression is not an integral constant expression
case v2.x:
     ^ error: case value is not a constant expression
```

The tested scalar-alias workaround fails because its initializer is likewise
not a constant expression; `constexpr` is not a DXC keyword.

Compiler Explorer: **https://godbolt.org/z/51xjeKra5**. FXC accepts the tested
FXC-compatible forms. Clang accepts `(10).x`, the exact filed case; its rejections of
`static const uint2` forms use the ordinary C++ non-`constexpr` rule and become
accepted when spelled `constexpr uint2`.

DXC explicitly excludes `HLSLVectorElementExprClass` and
`ExtMatrixElementExprClass` in
[`CheckICE`](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/tools/clang/lib/AST/ExprConstant.cpp#L9035-L9036).
The existing
[`const-expr.hlsl` test](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e6a9019e4e0823746470f3ab75341d6b/tools/clang/test/SemaHLSL/const-expr.hlsl#L379-L382)
records the FXC divergence with “It would be desirable to have this supported,”
so a fix must update that test.

The remaining question is which constant-expression rule DXC should use.
Suggested labels: `hlsl-next` and `usability`; keep `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
