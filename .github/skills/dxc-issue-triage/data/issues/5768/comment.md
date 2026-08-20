> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5768](https://github.com/microsoft/DirectXShaderCompiler/issues/5768).

Still reproduces on `main` (commit `89e2f98e2`, `main-debug`). Compiling

```hlsl
float4 main(float V : SV_VertexID) : SV_Position {
   return V;
}
```

with `-T vs_6_0` gives:

```
error: validation errors

error: SV_VertexID must be uint.
Validation failed.
```

The shader still passes the front end and is only rejected once DXIL is emitted and
validated, exactly as reported.

Confirmed across every probeable stable release from v1.4.1907 through v1.9.2607 (linear
scan, no transitions) and on Compiler Explorer's oldest (`dxc_1_6_2112`) and rolling
`dxc_trunk` builds alike:
https://godbolt.org/z/PWdbvjGP3

This isn't unaddressed: PR #3043 added exactly this class of check (including a
`SV_VertexID`-specific test) and merged in Feb 2021, but was reverted five days later "due to
regressions," with a note to re-merge once fixed. That never happened — both the merge and
the revert land entirely between two stable releases (v1.5.2010 and v1.6.2104), so no
released `dxc` ever shipped the check, and no follow-up has landed since.

Current labels (`bug`, `tech-debt`, `diagnostic`) already fit well. Given the type-system
angle and the fact that today's rejection point is the validator, consider adding
`type-system` and `validation`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
