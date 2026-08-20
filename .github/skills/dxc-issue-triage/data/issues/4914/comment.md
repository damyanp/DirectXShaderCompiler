> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4914](https://github.com/microsoft/DirectXShaderCompiler/issues/4914).

Still reproduces on `main` (public upstream commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
Debug build) and on every stable release checked, v1.4.1907 (2019-07) through v1.9.2607
(2026-07-29) — the full checkable release history, three and a half years before this report:

```hlsl
struct S {
    int value;
    S getThis() { return this; }
    void copyThisInto(out S dst) { dst = this; }
};
```

```
error: cannot compile this aggregate expression yet
        return this;
               ^~~~
```

The gap is narrow and CodeGen-specific, not a language/design limitation: Sema already accepts
this without complaint (see the currently-passing `-fsyntax-only` test
`tools/clang/test/HLSL/cpp-errors.hlsl:563`, `CInternal getSelf() { return this; }`, no
`expected-error` attached). `HLSLExternalSource`/`genereateHLSLThis` gives `this` value-type
semantics (an lvalue of type `S`, not `S*`), so returning or assigning `this` by value is an
aggregate expression — and `AggExprEmitter` in `CGExprAgg.cpp` has no `VisitCXXThisExpr`
override (unlike the scalar emitter), so it falls into the generic
`"cannot compile this %0 yet"` diagnostic. `this.member` access is unaffected (confirmed with a
same-shape control) because it never reaches the aggregate emitter as a bare `this`.

This is also DXIL-specific: the identical `repro.hlsl`, same command plus `-spirv`, compiles
cleanly and folds correctly — confirming @Keenuts's comment above by re-running it directly.
FXC also compiles the identical struct/member-function shape cleanly. The new Clang-based HLSL
front end (`hlsl_clang_trunk`) reproduces the byte-identical diagnostic, so the gap is not
DXC-legacy-only. [Compiler Explorer: FXC succeeds, `dxc_1_6_2112`/`dxc_trunk`/`hlsl_clang_trunk`
all fail identically](https://godbolt.org/z/jbqesq9P1).

Given that two independent compilers/backends already treat "copy the whole `this`" as ordinary
code, this reads more like an unimplemented single CodeGen visitor than an open design question.
Suggest adding `bug` alongside the existing `enhancement`/`question`/`dxil`/`fxc-disagrees`
labels; leaving `question` in place since it does capture the original, reasonable "should this
even be supported" concern raised when this was filed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
