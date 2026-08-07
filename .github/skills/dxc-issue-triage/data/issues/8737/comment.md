> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#8737](https://github.com/microsoft/DirectXShaderCompiler/issues/8737).

Both symptoms reproduce on `main` (`1.9.0.15422 (main, eff900d54)`), and both have been present
since **v1.7.2207** — the first release with SM 6.7. Not a regression: no release that can
compile the repro has ever behaved differently. Compiler Explorer, including your 1.10.2605.24:
<https://godbolt.org/z/ea91a6vnj>

**ICE.** `InterlockedMax(tex.sample[s][uv], …)` exits `0x80004005` with

```
error: llvm::cast<X>() argument of incompatible type!
```

This is an internal failure, not a diagnosed error — `llvm::llvm_cast_assert_internal` throws
`hlsl::Exception(DXC_E_LLVM_CAST_ERROR, …)` (`lib/Support/ErrorHandling.cpp:143`), so it is
identical in Debug and Release. It also fires with `InterlockedAdd` and a constant sample index,
and on `RWTexture2DMSArray`. A `tex.sample[s][uv] = v` **store** compiles clean, so the double
subscript itself is fine; only an atomic through it fails.

**Silent case — the analysis in the report checks out, and the DXIL shows it.** The
implicit-sample form compiles with exit 0 and no diagnostic at all, not even a warning:

```llvm
; tex                                   UAV     u32        2dMS      U0             u0     1
%6 = call i32 @dx.op.atomicBinOp.i32(i32 78, %5, i32 7, i32 %3, i32 %4, i32 undef, i32 -559038737)
                                                                       ^^^^^^^^^^
call void @dx.op.textureStoreSample.i32(i32 225, %7, i32 %3, i32 %4, i32 undef, …, i8 15, i32 0)
call void @dx.op.textureStoreSample.i32(i32 225, %8, i32 %3, i32 %4, i32 undef, …, i8 15, i32 %2)
```

The stores carry a `sampleIdx` operand; the atomic has none and its last coordinate is `undef` —
not a defaulted 0. The same `InterlockedMax` on a non-multisampled `RWTexture2D` emits a
byte-identical instruction, which is correct there: `docs/DXIL.rst:1876-1887` gives `RWTexture2D`
two active coordinates. **DXC lowers the multisampled and non-multisampled cases identically.**
`TranslateAtomicBinaryOperation` (`lib/HLSL/HLOperationLower.cpp:4906`) initialises all three
coordinates to `undef` and fills only as many as the address vector has, with no multisample
branch, so there is no path that could supply a sample index.

`RWTexture2DMSArray` is worse rather than equivalent: the address is a `uint3`, so all three
coordinate slots hold x/y/slice and there is no free operand at all.

**This is invalid input DXC fails to diagnose, not valid input DXC miscompiles.**
`docs/DXIL.rst:1876-1887` does not list `Texture2DMS` or `Texture2DMSArray` among `AtomicBinOp`'s
valid resource types, and `RWTexture2DMSMethods` (`utils/hct/gen_intrin_main.txt:927`) declares
no interlocked method — both forms reach the free `InterlockedMax(ref …)` overload, so Sema never
sees the resource kind. The Desired Outcome in the report is the right shape of fix; no codegen
change can substitute for it while `atomicBinOp` has no sample-index variant.

Nothing downstream catches it either. The validator's `AtomicBinOp` case
(`lib/DxilValidation/DxilValidation.cpp:2412`) checks the overload type and that the handle
is a UAV, but not the resource *kind*, so `-Fo` on the implicit form produces a validated
container. A validation rule may be worth considering alongside the front-end diagnostic.

Label suggestion: add `crash` (an internal failure — `bug` alone understates it),
`incorrect-code`, `diagnostic`, `sm6.7`; remove `needs-triage`. Not proposing `correctness`,
since correct behaviour here is rejection rather than different codegen. We may be missing
history behind the current labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
