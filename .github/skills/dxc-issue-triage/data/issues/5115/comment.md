> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5115](https://github.com/microsoft/DirectXShaderCompiler/issues/5115).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), with the exact
diagnostic quoted above. It reproduces the same way on every stable release checked,
`v1.4.1907` (2019-07) through `v1.9.2607` (2026-07) — this has never worked as gcc's C++ rules
would suggest, on any release we can measure.

Compiler Explorer: https://godbolt.org/z/xPz8ndv7T

- `dxc_1_6_2112` and current `dxc_trunk` both still report `f(1)` as ambiguous.
- The new Clang-based HLSL front end (`hlsl_clang_trunk`) compiles the identical source with
  **no diagnostic at all**. That matches what @llvm-beanz described above: the HLSL 202x
  overload-rules rewrite adopts C++ overload rules, and it looks like this specific case is
  already fixed there. (Checked that this isn't just Clang being permissive: a
  genuinely-ambiguous variant, `f(1.0f)` against the same two overloads, is correctly rejected
  by both `dxc_trunk` and `hlsl_clang_trunk`, with identical wording.)

So current (classic) `dxc` still has the reported behavior, and it's not new — nothing to
close here — but the successor front end already resolves it the way this issue asks for.

Suggested labels: keep `bug` and `hlsl-next`; consider adding `diagnostic` (the symptom is
specifically a wrong/unjustified diagnostic on valid input) and `type-system` (the underlying
defect is in how integer-literal arguments are ranked against `int`/`unsigned int` overloads).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
