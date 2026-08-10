> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3883](https://github.com/microsoft/DirectXShaderCompiler/issues/3883).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and it has never worked:
`bisect --linear` scores all 20 stable release binaries from v1.4.1907 (2019-07)
through v1.9.2607 (2026-07), plus a clean Debug build of `main`, as internal
failures.

```
$ dxc -T ps_6_0 -E PSMain repro.hlsl        # Debug main
Internal compiler error: LLVM Assert        # exit 0xE0000001

Error: assert(this->getType()->isVectorTy() && "Only valid for vectors!")
File:  lib/IR/Constants.cpp(1419)
    llvm::Constant::getSplatValue
    llvm::Constant::getUniqueInteger
    `anonymous namespace'::TranslateCBGepLegacy
    `anonymous namespace'::TranslateCBAddressUserLegacy
    `anonymous namespace'::TranslateCBOperationsLegacy
```

`TranslateCBGepLegacy` (`lib/HLSL/HLOperationLower.cpp:8871`) tests the cbuffer index with
`dyn_cast<Constant>` and then calls `getUniqueInteger()` on it. `UndefValue` *is* a
`Constant`, so the undefined index goes straight through. Under `NDEBUG` the asserts are
compiled out and the value reaches `getAggregateElement(0U)` →
`UndefValue::getNumElements()` → `Type::getStructNumElements()`, which is a bare
`cast<StructType>` on an `i32` and throws `DXC_E_LLVM_CAST_ERROR`. That is the release
symptom, reproducible from the same Debug binary by continuing past both asserts under a
debugger.

**Two things worth adding to the report.**

1. **The self-initialisation is not the trigger.** Plain `uint index; return colors[index];`
   fails identically, and the only thing it prints is the internal cast failure — no
   `-Wuninitialized` warning, nothing pointing at the variable. That warning fires only on the
   `index = index` spelling, and it has never stopped codegen. The same undefined index
   outside the cbuffer path (a `Buffer<float4>`) compiles at exit 0 and emits
   `bufferLoad(..., i32 undef, i32 undef)`. So this input is either an internal failure or an
   unguarded `undef` in the DXIL, and never an error.

2. **FXC already diagnoses it**, on both spellings:
   `error X4000: variable 'index' used without having been completely initialized`. The
   initialised form compiles cleanly under FXC, so that is the diagnostic and not a general
   FXC objection to the shader.

Compiler Explorer, FXC beside DXC 1.6.2112 and trunk: https://godbolt.org/z/6c9h3r4a3

The same defect has had five presentations without ever being fixed: an access violation
with empty stderr; an access violation with a message; `0x80AA001D`; plain `E_FAIL` plus the
build-agnostic `cast<X>() argument` marker; and the Debug LLVM assert above. Worth knowing
before reading any old "does this still repro?" note: the current spelling looks like an
ordinary compile error, and CE's Linux builds print `cast<X>()` where Windows prints
`llvm::cast<X>()`.

Suggested labels: add `fxc-disagrees` (measured above) and `diagnostic` (the ask is a
diagnostic in place of an internal failure). Existing labels all look right.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
