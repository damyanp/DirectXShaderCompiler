> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5395](https://github.com/microsoft/DirectXShaderCompiler/issues/5395).

Confirmed: still reproduces on `main` (Debug build, commit `89e2f98e2`, 2026-08-19). Compiling
the repro with `-T ps_6_6 -HV 2021` produces no `-Wfor-redefinition` warning, while the
identical source under `-HV 2018` still does:

```
repro.hlsl:6:18: warning: redefinition of 'i' shadows declaration in the outer scope; most recent declaration will be used [-Wfor-redefinition]
       for (uint i = 0; i < 3; i++) {
                 ^
```

This reproduces on every DXC release that has ever supported `-HV 2021` -- v1.6.2112
(2021-12-08, the release that added the flag) through v1.9.2607, and `main`. It is not a
regression: the warning is tied to a `-HV`-gated `Scope::ForDeclScope` marker
(`ParseStmt.cpp`) that made the pre-2021 for-loop variable leak into, and merge with, the
enclosing scope's declaration of the same name -- `warn_hlsl_for_redefinition` exists to
soften what would otherwise be a same-scope `redefinition` error. HLSL 2021 gives the loop
variable a real nested scope instead, so there is no same-scope redefinition event left for
that diagnostic to describe.

More generally, DXC has no `-Wshadow`-style diagnostic for ordinary block-scope shadowing in
*either* language mode -- an inner `{ }` block redeclaring an outer variable produces no
warning under `-HV 2018` either. So this isn't a case of an existing check losing its target;
resolving it would mean adding a new shadow diagnostic for HV2021+ scoping, not restoring old
behavior.

Compiler Explorer (`dxc_1_6_2112`, `dxc_trunk`): https://godbolt.org/z/KzYb6cKTE -- both
compile clean, no warning.

Suggest adding the `diagnostic` label alongside the existing `bug`/`hlsl2021` -- this is
squarely a diagnostic-coverage question. Whether it should stay `bug` or move to
`enhancement` is a maintainer call: nothing regressed, but adding shadow detection for the new
scoping rules seems like a reasonable ask.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
