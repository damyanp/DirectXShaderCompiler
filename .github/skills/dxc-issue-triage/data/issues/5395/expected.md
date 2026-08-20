# Expected symptom (written before running anything)

Issue: https://github.com/microsoft/DirectXShaderCompiler/issues/5395

**Claim:** Before HLSL 2021, declaring a `for`-loop induction variable that shadows a
variable already declared in an outer scope produces the warning:

```
warning: redefinition of 'i' shadows declaration in the outer scope; most recent
declaration will be used [-Wfor-redefinition]
```

With `-HV 2021`, compiling the exact same shader produces **no such warning** (and no
other diagnostic about the shadowing) even though the shadowing itself still occurs
semantically (the inner `i` is what is used inside the loop, the outer `i` is what is
returned).

**"Reproduces" means:** compiling the reporter's repro with `-T ps_6_6 -HV 2021 repro.hlsl`
emits **no** `-Wfor-redefinition` / shadow-related warning in the combined output, while
compiling the same source with `-HV 2018` (or no `-HV`, which predates 2021) **does** emit
that warning. I.e. the symptom is an *absence* of a diagnostic that a control run proves the
compiler is capable of producing on the same input under an older language mode.

**Repro quality:** `complete` — the issue body contains the full shader (`repro.hlsl` below,
verbatim) and the exact `RUN:` line (`%dxc -T ps_6_6 -HV 2021 %s`), plus the expected old-mode
warning text to use as a control target.

**Not compiler-verifiable aspects:** none identified; this is a pure diagnostic-emission
question decidable from `dxc` stdout/stderr alone.
