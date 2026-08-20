> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5563](https://github.com/microsoft/DirectXShaderCompiler/issues/5563).

This is fixed on current `main` (source-equivalent to
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`; the local Debug binary self-reports
`7665270b9`). The filed command (`-T ps_6_0 -E PSMain -spirv -HV 2021`) now
exits 0 and emits valid SPIR-V; forcing `-Od` so the optimizer cannot simply
eliminate the unused local confirms the static member reference is correctly
resolved to `true` rather than the fatal error just being dead-code-eliminated
away.

Stable-release testing places the fix in **v1.9.2602**: `v1.8.2505.1` still
fails with the exact reported diagnostic (`found unregistered decl`, same
source location, exit `0x80004005`), while `v1.9.2602` compiles successfully.
[Compiler Explorer](https://godbolt.org/z/Y1W7q714v) shows the same contrast:
dxc 1.6.2112 fails with the reported error, trunk succeeds.

The most likely fix is
[`1e3da156b`](https://github.com/microsoft/DirectXShaderCompiler/commit/1e3da156b7aeab25b7e891010e579902322845ed)
("Handle partial template class specialization", #7673), which stopped the
SPIR-V backend from generating code directly off the un-instantiated partial
specialization decl. It also fixed #7007, an independently filed near-duplicate
with the identical diagnostic text on a different template. A second commit
in the same window,
[`b9af1ec44`](https://github.com/microsoft/DirectXShaderCompiler/commit/b9af1ec44364a5d359af82bee5adce7ee7fca76a)
("Folding global constant variables", #7786), also touches the exact code path
that raised this error and may have contributed. Both are confirmed by commit
ancestry to fall inside the `v1.8.2505.1` → `v1.9.2602` window; neither was
verified by building and testing the commit in isolation, so treat the
attribution as strong rather than certain.

The existing `bug` and `spirv` labels remain accurate; no label change is
suggested. The issue can be closed as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
