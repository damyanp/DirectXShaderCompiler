> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5999](https://github.com/microsoft/DirectXShaderCompiler/issues/5999).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`1.9.0.5465-triage`), consistent with @llvm-beanz's/@pow2clk's diagnosis above. Re-running the
distilled repro from [the CE link posted in this thread](https://godbolt.org/z/z4TnxrKqr):

```
repro.hlsl:18:5: warning: implicit conversion from 'globallycoherent RWByteAddressBuffer' to 'RWByteAddressBuffer' loses globallycoherent annotation [-Wconversion]
    TemplateFunction(SomeBuffer);
    ^
```

`ExplicitFunction(SomeBuffer)` (explicitly typed) still emits no warning, matching the original
asymmetry @simonwongms reported.

History floor: this repro shape is only probeable from v1.7.2308 (2023-08-14) onward, because
earlier releases fail with `'template' is a reserved keyword in HLSL` — HLSL function templates
didn't exist yet. Every stable release from v1.7.2308 through the current v1.9.2607 reproduces
it identically. [Updated CE link](https://godbolt.org/z/E16q13zKa) adds CE's oldest DXC (1.6.2112,
same template-keyword failure) alongside current trunk. I also tried the Clang-based HLSL front
end (`hlsl_clang_trunk`), since @llvm-beanz noted Clang implements attributes so they survive
canonicalization — but it doesn't yet parse `globallycoherent` for this repro, so it can't
answer that question right now.

The thread still describes this as the known qualifier-as-attribute canonicalization
limitation, and nothing in the linked comments points to a landed fix. Existing labels (`bug`,
`hlsl2021`, `shader-linking`, `type-system`) all still fit; no change proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
