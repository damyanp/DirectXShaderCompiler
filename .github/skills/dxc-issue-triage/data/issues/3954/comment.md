> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3954](https://github.com/microsoft/DirectXShaderCompiler/issues/3954).

This no longer reproduces. The shader from the report compiles cleanly on `main`
(1.9.0.5433, [`13730886e`](https://github.com/microsoft/DirectXShaderCompiler/commit/13730886e)),
using the oldest profile that can express `[shader("anyhit")]`:

```
dxc -T lib_6_3 repro.hlsl
```

I checked every stable release that ships a `dxc` binary — 20 of them. It failed on every one
from v1.4.1907 (2019) through v1.8.2407, and passes from **v1.8.2502** onward — a single clean
transition:

| | |
| --- | --- |
| v1.8.2407 | `error: Unexpected matrix subscript use.`<br>`UNREACHABLE executed at C:\__w\1\s\DXC\lib\HLSL\HLMatrixSubscriptUseReplacer.cpp:93!` |
| v1.8.2502 | compiles, exit 0 |

Your quoted output matches v1.6.2106 and v1.6.2112 exactly, line 91 included, which fits the
September 2021 filing date.

The same defect reports itself four ways depending on release. v1.4.1907 and v1.5.2010 die
with an access violation and **completely empty stderr**; v1.6.2104 says only `Internal
compiler error: LLVM Unreachable`; v1.6.2106/v1.6.2112 print the message you quoted; v1.7.2207
through v1.8.2407 print it as an `error:` and exit with E_FAIL. Searching for the message text
alone would place the start of this bug in 2021 rather than at or before 2019.

**Cause and fix.** `HLMatrixSubscriptUseReplacer::replaceUses` handles only loads and stores of
a matrix-subscript pointer. Before the fix, `Param.Matrix[2].r.xxx` left `.r` as an lvalue, so
codegen emitted `bitcast float* %5 to <1 x float>*` on that pointer — neither a load nor a
store, so the pass hit the `llvm_unreachable`. Afterwards the front end loads the whole
`<3 x float>` and `extractelement`s from it, and the pass never sees the shape.

That points at [`0372fb792`](https://github.com/microsoft/DirectXShaderCompiler/commit/0372fb792)
("Fix assertion on splat of groupshared scalar", #6930), which adds the missing
`CK_LValueToRValue` in `LookupVectorMemberExprForHLSL` when a swizzle has duplicate elements. It
is in v1.8.2502 and not in v1.8.2407, and the duplicate-element condition matches the observed
behaviour on the last broken release: `Param.Matrix[2].r.x` compiles there, `Param.Matrix[2].r.xx`
crashes. I did not build at that commit, though, and there are 133 commits between the two tags,
so treat this as a strong attribution rather than a bisected result.

**The generated code is correct, not just non-crashing.** On both v1.8.2502 and `main`, the
original shader and your `Param.Matrix[2].xxx` workaround produce byte-identical DXIL — one
`cbufferLoadLegacy`, `extractvalue ..., 2` for the column-major `M[2][0]`, three `fmul`s. The
workaround is no longer needed.

On "seems to only happen with Ray Tracing shaders": the identical subscript in a `cs_6_0`
shader failed the same way on v1.4.1907, v1.6.2106, and v1.8.2407, so the trigger appears to be
the swizzle rather than the shader stage, consistent with the fix landing in Sema.

Side-by-side on Compiler Explorer (v1.6.2112 vs trunk): <https://godbolt.org/z/PT7Yqj1r6>. Note
that CE's Linux builds report the old-compiler failure as a bare `SIGSEGV` with no message; the
text above is from the Windows release binaries.

Suggest closing as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
