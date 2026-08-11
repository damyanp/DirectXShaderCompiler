> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4701](https://github.com/microsoft/DirectXShaderCompiler/issues/4701).

Still reproduces on `main` (`13730886e`) and all 20 stable releases from
v1.4.1907 through v1.9.2607. The final DXIL still contains both the reported
TGSM allocation and its never-read store:

```llvm
@"\01?a@@3PAMA" = external addrspace(3) global [10 x float], align 4
  store float 1.000000e+00, float addrspace(3)* getelementptr inbounds ([10 x float], [10 x float] addrspace(3)* @"\01?a@@3PAMA", i32 0, i32 0), align 4, !tbaa !7
```

The identical `static` and function-local arrays are removed on every one of
those releases, while a genuinely live `groupshared` control remains visible.
The result is unchanged at the default `-O3`, `-O1`, and `-Od`.

This has a compile-time consequence. Scaling the dead TGSM array to 64 KB
produces:

```text
case-budget-groupshared.hlsl:9:10: error: Total Thread Group Shared Memory used by 'main' is 65536, exceeding maximum: 32768.
```

The static twin compiles to `ret void`. Whether the budget should be checked
before or after this optimisation is a design question; no GPU/runtime effect
was measured.

**Other compilers.** FXC (`fxc /T cs_5_0`) removes it entirely — no `dcl_tgsm`, ~1 instruction
slot. The clang-based HLSL front end currently keeps it, same as DXC. All panes:
<https://godbolt.org/z/b9KE6as36>

`-fcgl` shows why the generic passes miss it: TGSM is emitted as an external
address-space-3 global with no initializer, while the static twin is an
internal initialized global. `GlobalOpt::ProcessGlobal`
(`GlobalOpt.cpp:1707,1720`) rejects the former, and
`LowerStaticGlobalIntoAlloca` requires `IsStaticGlobal`
(`DxilUtil.cpp:114`), which excludes address space 3. A safe fix still needs
module-wide liveness because a TGSM store is dead only when no load exists.

Suggested label: `fxc-disagrees` alongside the existing `performance`. No `check-in-clang` —
clang was checked and behaves the same.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
