> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#6082](https://github.com/microsoft/DirectXShaderCompiler/issues/6082).

Confirmed: the reported IR shape still reproduces on `main`
(`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`) and is unchanged all the way back to v1.6.2104,
the oldest release that accepts `-T lib_6_6` (v1.4.1907 and v1.5.2010 predate that profile).
`dxc -T lib_6_6` on the repro still emits:

```llvm
%class.matrix.bool.1.2 = type { [1 x <2 x i1>] }
...
  %2 = bitcast %class.matrix.bool.1.2* %1 to <2 x i32>*
  %3 = load <2 x i32>, <2 x i32>* %2, align 4
```

byte-for-byte identical to the issue body, on the current build, on CE's oldest DXC
(`dxc_1_6_2112`), and on `dxc_trunk`:
https://godbolt.org/z/zxjbnx5dE

For contrast, a `bool2` **vector** field in the same payload struct does not hit this pattern
— it's already represented directly as `<2 x i32>` with a plain integer load, no bitcast.
Only bool **matrices** take this path.

DXC's own validator accepts this output with no errors or warnings, which lines up with
@llvm-beanz's point above: this isn't a claim about DXIL being invalid by DXC's own rules,
only about what happens if the container is reinterpreted as standard/modern LLVM IR (as the
follow-up `opt -passes="vector-combine,instcombine"` example does) — and that reinterpretation
is exactly what the reporter's real-world reproducer relies on.

This needs the design discussion the thread was already heading toward rather than a compiler
fix-or-close decision based only on repro status. The last comment (2024-04-10) was waiting on
@tex3d; nothing
has landed here since, and the only related activity is upstream, in the new LLVM-based HLSL
frontend (`llvm/llvm-project#91639`, "[HLSL] Boolean vector support"), consistent with
@llvm-beanz's stated plan to handle DXIL→valid-LLVM-IR legalization there rather than in this
repository.

Suggested label additions: `correctness`, `matrix-bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
