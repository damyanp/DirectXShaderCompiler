> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2188](https://github.com/microsoft/DirectXShaderCompiler/issues/2188).

Still reproduces on `main` (1.9.0.15422, `eff900d54`), and in every release from
**v1.4.1907** (2019-07) to **v1.9.2607** — 20 releases, linear scan, no transition.

```
repro.hlsl:10:27: error: variable length arrays are not supported in HLSL
groupshared float4      S1[cThread];
repro.hlsl:12:2: error: 'numthreads' attribute requires an integer constant
[numthreads(c2Thread.x, c2Thread.y, 1)]
```

Compiler Explorer, FXC beside DXC and clang: **https://godbolt.org/z/nvqTPYffM**
FXC compiles it and folds the constants (`dcl_thread_group 8, 8, 1`); the same is true of
a local FXC 10.1 from the Windows SDK.

**The trigger is narrower than the title suggests.** `static const` is not the problem —
reading a *component of a const vector* is. Each of these was compiled separately:

| construct | DXC |
| --- | --- |
| `static const uint cThread = 64; groupshared float4 S1[cThread];` | compiles |
| `static const uint eight = 8; [numthreads(eight, 8, 1)]` | compiles |
| `static const uint2 c2Thread = {8,8}; groupshared float4 S1[c2Thread.x*c2Thread.y];` | error |
| `[numthreads(c2Thread.x, c2Thread.y, 1)]` | error |

So both halves of the report are one defect: a component read of a `const` vector is not
a constant expression. The `uint2(8,8)` constructor is not involved (brace-init fails the
same way), and `-HV 2021` makes no difference.

Not the same as #2191, despite the shared function: there a `static const` **scalar**
passes the constant-expression check and the failure is an assert in later bookkeeping.
Here the check itself fails, on every release. Related, but separate fixes.

This is codified in DXC's own tests — `tools/clang/test/SemaHLSL/const-expr.hlsl`:

```
// Note: here dxc is different from fxc, where a const integral vector can be used in ICE.
// It would be desirable to have this supported.
float arr_vc_One[vc_One.x];  /* expected-error {{variable length arrays are not supported
                                in HLSL}} fxc-pass {{}} */
```

with the same pattern for attributes at `attributes.hlsl:659`
(`[maxvertexcount (sc_count4.w)]`). Any fix has to update those expectations.

Mechanically: `ValidateAttributeIntArg` (`SemaHLSL.cpp:13889`) tests `isCXX11ConstantExpr`
and returns `0` when it fails — once per component, which is why the `numthreads` error
appears twice. `numthreads` then computes a group size of 0, warns
`Group size of 0 (0 * 0 * 1) is outside of valid range`, and drops the attribute, which
produces a fourth error, `compute entry point must have a valid numthreads attribute`.
The array bound reaches `err_hlsl_vla` (`SemaType.cpp:2144`) for the same reason.

Two things that have changed since 2019:

- That warning and the fourth error first appear in **v1.8.2403** (2024-03); v1.7.2308
  (2023-08) and earlier print only the three errors. The rejection itself is unchanged.
- `clang-dxc` **rejects it too**, with a clearer explanation
  (`note: initializer of 'cThread' is not a constant expression`). The inlined-constant
  version compiles there, so this is the same gap rather than an unrelated front-end
  limitation. Whatever is decided here likely needs deciding for both compilers.

The `#define` workaround from @tristanlabelle's 2019 comment still applies.

Suggested labels: add **`type-system`** and **`hlsl-next`** — this is a change to what HLSL
treats as a constant expression. No removals; `fxc-disagrees` is confirmed by running FXC.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
