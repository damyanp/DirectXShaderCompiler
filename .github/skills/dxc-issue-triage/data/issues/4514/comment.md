> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4514](https://github.com/microsoft/DirectXShaderCompiler/issues/4514).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on all 20 stable
releases from v1.4.1907 to v1.9.2607:

```
repro.hlsl:15:9: error: no member named 'testVariable' in namespace 'testNamespace'; did you mean simply 'testVariable'?
    if( testNamespace::testVariable * tid.x > 0 )
        ^~~~~~~~~~~~~~~~~~~~~~~~~~~
        testVariable
```

The result is unchanged under `-HV 2016`, `2017`, `2018` and `2021`.

Source and controls point to the declaration context. `HLSLBufferDecl::Create`
uses the translation unit as the semantic parent for `cbuffer`/`tbuffer`
(`SemaHLSL.cpp:15420`), while the namespace is only the lexical parent.
Because `HLSLBufferDecl` is transparent (`DeclBase.cpp:913`), the member is
visible unqualified from the translation unit but is missing from qualified
namespace lookup.

The reported `Texture2D` workaround is incidental: a preceding namespace-scope
`static uint` or `struct` also makes lookup succeed. A second `cbuffer` does
not, and moving the extra declaration below `main` makes the error return.
`tbuffer` is affected too.

[Compiler Explorer](https://godbolt.org/z/1497YdPj1) shows DXC 1.6.2112,
trunk, and the workaround. The two Clang panes show the inverse lookup:
`testNamespace::testVariable` is accepted and the unqualified spelling is
rejected.

The existing `bug` label still fits; no label change is suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
