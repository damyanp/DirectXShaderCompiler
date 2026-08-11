> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4721](https://github.com/microsoft/DirectXShaderCompiler/issues/4721).

Still open and still accurate, but the gap is narrower than the title
suggests: `dxc` already computes fix-its and prints them — there is just no
way to ask it to apply them.

On `main` (`13730886`):

```text
dxc failed : Unknown argument: '-fixit'

repro.hlsl:12:18: error: operands for short-circuiting logical binary operator must be scalar, for non-scalar types use 'and'
  bool4 mask = a && b;
               ~~^~~~
               and(a, b)
```

`and(a, b)` is a `FixItHint::CreateReplacement` from `SemaHLSL.cpp:10713`, and
pasting it in compiles clean. All 20 stable releases v1.4.1907–v1.9.2607
reject `-fixit`; on this build so do `-fixit=hlsl`, `-fixit-recompile` and
`-Xclang`, and `-help` documents none of them. (`/fixit` "succeeds" only
because dxc silently drops unrecognised `/`-flags: it produces an object
byte-identical to no flag at all.)

The machinery is in the tree and already linked into `dxcompiler`:
`FixItRewriter.cpp` in `clangRewriteFrontend`, `case FixIt: return new
FixItAction();` in `ExecuteCompilerInvocation.cpp:53`, `-fixit` still declared
in `CC1Options.td:396`. What is missing is a driver route to it —
`HLSLOptions.td` declares neither `fixit` nor `Xclang`, so nothing selects
that action.

llvm-project's HLSL clang exposes `-Xclang -fixit` and reports:

```text
<source>:12:17: note: FIX-IT applied suggested code changes
```

That is a different fork, so this tree's inherited `-cc1 -fixit` path remains
unmeasured; proving it would require building the optional `clang.exe`.
[Compiler Explorer](https://godbolt.org/z/af7P4dYvc) shows both compilers.

Two implementation caveats are already measurable. First, `dxr` prints the
same hint and exits 0 but emits `bool4 mask;`; the fixed-input control preserves
`bool4 mask = and(a, b);`. Second, from v1.7.2207 through v1.8.2407 the
suggested replacement itself fails with `error: Invalid record`, even under
`-Vd`; it compiles from v1.8.2502.

Suggested labels: `enhancement`, `diagnostic`, and `rewriter`, alongside
`hlsl-next`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
