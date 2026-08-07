> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3150](https://github.com/microsoft/DirectXShaderCompiler/issues/3150).

**1. The planned documentation note is still absent.** @damyanp's 2024-07-03 plan was to
document in `DXIL.rst` that `sdiv` divide-by-zero is undefined. Current `DXIL.rst` mentions
divide-by-zero only for the DXIL `UDiv` *operation* ("returns 0xffffffff for both quotient and
remainder"), not the LLVM `sdiv`/`udiv` *instructions*.

**2. DXC still emits the LLVM instructions, not the DXIL operation** (`main`, 1.9.0.15422):
`sdiv i32 %5, %6` / `udiv i32 %9, %10`, matching @llvm-beanz's description.

**3. DXC-produced DXIL does not reach the validator's div-by-zero rules.**
`INSTR.NOIDIVBYZERO` / `INSTR.NOUDIVBYZERO` in `DxilValidation.cpp` apply only to a *literal
constant* zero denominator. DXC folds `a / 0` to `undef` before validation; for the tested
shader, the diagnostic is:

```
error: Assignment of undefined values to UAV.
```

This still holds with `-Od`; the rules can therefore fire only on DXIL from other producers.

Suggested label: `dxil`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
