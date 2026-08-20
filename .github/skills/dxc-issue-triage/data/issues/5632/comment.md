> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5632](https://github.com/microsoft/DirectXShaderCompiler/issues/5632).

Still reproduces on `main` (public commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`) and on
Compiler Explorer's `dxc_trunk`.

## The DXIL crash (@llvm-beanz's repro)

```
$ dxc -T ps_6_0 repro.hlsl
Internal compiler error: LLVM Assert
```

The underlying assert is `llvm::StoreInst::AssertOK`, `"Ptr must be a pointer to Val type!"`,
reached from `CodeGenFunction::EmitHLSLVectorElementExpr` — the construct-cast
`float(obj._pad)` leaves an array-typed lvalue where CodeGen expects a scalar, and the
resulting store mismatches types. Release builds don't hit that assert (compiled out) but hit
the same defect one step later via the release-path `llvm::cast<X>()` check:

```
error: llvm::cast<X>() argument of incompatible type!
```

Every stable release from v1.4.1907 (2019-07) through v1.9.2607 — 20 releases — fails this
input, either with one of the two asserts above or — uniquely at v1.5.2010 — with a
self-detected `error: Invalid record` when DXC tries to re-read the module it just emitted.

Link: https://godbolt.org/z/W9Kr6fvPa (`dxc_trunk` crashes on the same defect; `dxc_1_6_2112`
cannot compile the original `ps_6_7` variant used in that CE case).

## The missing diagnostic

The SPIR-V path still emits no warning or error for this construct — codegen silently reads
element 0, matching FXC. That's not itself a bug (per the earlier discussion in this thread),
but it is worth noting DXC *does* check construct-cast element counts in general: changing the
array to two elements produces `error: too many elements in vector initialization (expected 1
element, have 2)`. A single-element array is specifically treated as compatible with a scalar
destination with no diagnostic — the same unchecked case that reaches the crashing DXIL path.

## Suggested labels

No changes — `bug`, `crash`, `dxil` and `diagnostic` already describe this precisely.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
