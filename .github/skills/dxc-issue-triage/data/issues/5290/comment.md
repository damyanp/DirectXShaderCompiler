> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5290](https://github.com/microsoft/DirectXShaderCompiler/issues/5290).

Still reproduces on `main` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df), and on
every stable release from v1.5.2010 (2020-10) through v1.9.2607 (2026-07) --
20 releases, no exceptions. v1.4.1907 predates the rewriter's
`-remove-unused-*` options entirely and can't run this repro at all.

Both examples in the thread still reproduce exactly as quoted:

```
$ dxr -remove-unused-functions -remove-unused-globals -E ps_main repro.hlsl
float4 ps_main(VS_OUTPUT input) : SV_Target0 {
  return float4(0, 0, 0, 0);
}
```

`struct VS_OUTPUT` is gone even though `ps_main`'s own signature still names
it. The second example (unused local `Material mtl = (Material)0;`) behaves
the same way: `struct Material` (and its nested `struct LayerColor`) are
dropped too.

**Root cause:** `CollectRewriteHelper`'s `VarReferenceVisitor`
(`tools/clang/tools/libclang/dxcrewriteunused.cpp`) only marks a type "used"
when some *other* expression later reads an already-declared variable via a
`DeclRefExpr`. Declaring a variable of a type -- including the entry point's
own parameter, or a local variable that is itself never subsequently read --
is not treated as a use of that type. That's one root cause for both
examples, not two: `entryFnDecl->parameters()` is never walked for this
purpose anywhere in this file's history. A control where the variable *is*
read afterward (`return input.color;` / `return mtl.colors[0].r;`) correctly
retains the type in both cases, isolating the trigger precisely.

@Snowapril's diagnosis in the first comment (iterate `entryFnDecl->params`
and remove those types from the unused set) targets the parameter half of
this; a full fix would need the same treatment for local-variable
declarations to cover the second example.

Suggest keeping this open and adding `correctness`, since the rewriter
produces HLSL that will not recompile.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
