> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3811](https://github.com/microsoft/DirectXShaderCompiler/issues/3811).

The validator gap still reproduces on `main` (`1.9.0.5433`, `13730886e`), but
the title's “no error/warning” is now stale for the exact filed shader. Since
v1.7.2308, dxc emits:

```
repro.hlsl:7:3: warning: parameter 'result' is uninitialized when used here [-Wparameter-usage]
                result += values[i];  // <-- This will not
                ^~~~~~
repro.hlsl:3:28: note: variable 'result' is declared here
```

Compilation still exits 0 and validation passes. The emitted `main` is
line-for-line identical to the DXIL in the issue, including:

```
%7 = phi float [ %10, %5 ], [ undef, %4 ]
%10 = fadd fast float %9, %7
%15 = phi float [ undef, %0 ], [ %10, %13 ]
```

The straight-line control remains rejected:

```
variant-straightline.hlsl:5:9: error: Instructions should not read uninitialized value.
note: at '%4 = fadd fast float %3, undef' in block '#0' of function 'main'.
Validation failed.
```

Exit is `0x80004005`. The asymmetry exists on both v1.4.1907 and v1.9.2607.

The mechanism is the explicit PHI exemption in
`lib/DxilValidation/DxilValidation.cpp`:

```cpp
if (isa<UndefValue>(op)) {
  bool LegalUndef = isa<PHINode>(&I);
  if (!LegalUndef)
    ValCtx.EmitInstrError(&I, ValidationRule::InstrNoReadingUninitialized);
}
```

The rule catches literal `undef` operands. Through the loop, the `fadd`
operand is a PHI and the PHI is exempt. That exemption dates to the repository's
first commit (`6ee4074a4`).

The warning is parameter-specific: with an uninitialized local, the same loop
still exits 0 with no warning or error and emits the same `undef`-seeded PHI.
The hole reproduces on all 20 measured releases; only silence has a boundary
(8 releases silent, 12 warning from v1.7.2308).

Compiler Explorer: **https://godbolt.org/z/57zn3j6YK**. It shows dxc 1.6.2112
silent, dxc trunk warning, and Clang trunk emitting a similar PHI without an
uninitialized-value diagnostic. The Clang pane stops before DXIL validation.

Keep `validation`; suggested additions are `incorrect-code`, `diagnostic` and
`check-in-clang`. Whether to track `undef` through PHIs in validation or add a
front-end diagnostic covering locals is a maintainer design decision.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
