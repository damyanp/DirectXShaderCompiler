> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5554](https://github.com/microsoft/DirectXShaderCompiler/issues/5554).

Still reproduces on `main` (commit `89e2f98e2`).

This thread narrowed a few times, so here's where it landed. The array-index half of the
original report (`partiboi[KEK::WAIT]` without a cast) is **not a bug** — real C++ rejects the
identical construct too, because a scoped enum doesn't implicitly convert to an integer for
subscripting; adding the cast, as the thread itself found, is correct.

The part that is still broken: a scoped enum's enumerator is not accepted as a non-type
template argument even when the template parameter's declared type is that exact enum type
(no conversion in question at all):

```
error: non-type template argument of type 'ENUM' is not an integral constant expression
```

The identical pattern with a plain (unscoped) `enum` compiles cleanly, and gcc accepts the
scoped-enum version outright (`-std=c++17`) — so this is a DXC-specific gap, not intended
behavior. Link with both DXC panes and a Clang pane for comparison:
https://godbolt.org/z/bqbP386nM

This is a duplicate of #6706, where a maintainer already stated: "we're not planning on
investing in fixing this in DXC. This won't be an issue in clang." That prediction now has
direct confirmation — the linked `hlsl_clang_trunk` pane compiles the same pattern cleanly.

One more thing worth flagging: the later comment linking
`godbolt.org/z/EGaesxvE1` ("concepts like `integral_constant<Enum,EnumVal>` are busted") uses
a **plain** enum in that specific link, which does compile — the underlying defect is real, but
that particular posted repro doesn't demonstrate it.

Labels: keeping `bug` and `hlsl2021`; adding `type-system` — DXC's constant-expression
evaluator not treating a scoped-enum enumerator as an integral constant expression in this
position is exactly that kind of inconsistency.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
