> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3259](https://github.com/microsoft/DirectXShaderCompiler/issues/3259).

**Still reproduces** on `main` (`1.9.0.5433 (triage, ab5400907)`), Debug build, on the shader
exactly as filed:

```
$ dxc -T as_6_5 -E main repro.hlsl
Internal compiler error: Terminal Error 0x80000003     # exit 0x80000003
```

The `DXASSERT` text only reaches `OutputDebugString`, so under a debugger:

```
Error:  !(Ty)
File:   lib\DXIL\DxilUtil.cpp(877)
Func:   hlsl::dxilutil::WrapInArrayTypes
  dxcompiler!hlsl::dxilutil::WrapInArrayTypes+0x5f
  dxcompiler!TranslatePtrIfUsedByLoweredFn+0x266
  dxcompiler!SROAGlobalAndAllocas+0x7b1
  dxcompiler!SROA_Parameter_HLSL::runOnModule+0x8a7
```

The debug flags in the report are not load-bearing — `-Zi -enable-16bit-types -Qembed_debug`
make no difference; they are dropped here so old releases have fewer ways to reject the input.

**It is not assert-only, so it is not confined to Debug builds.** All 19 releases that support
`as_6_5` — v1.5.2010 (2020-10, three weeks before this was filed) through v1.9.2607 — take an
access violation on the same input:

```
$ dxc -T as_6_5 -E main repro.hlsl
Internal compiler error: access violation. Attempted to read from address 0x0000000000000000
                                              # exit 0xC0000005
```

v1.4.1907 is the only release that does not crash, and only because it predates the profile
(`error: invalid profile as_6_5`). v1.5.2010 crashes with **no message at all** — of the
releases tested, v1.6.2104 is the first that prints that "Internal compiler error" line.
[Compiler Explorer](https://godbolt.org/z/8rxodd943) shows the Linux face of the same fault:
`dxc_1_6_2112` and `dxc_trunk` both terminate with `SIGSEGV`. Those are Release builds, so they
cannot show the assert; what they show is that removing the assert does not remove the bug.

**@jeffnn's 2020 diagnosis still holds.** `GetLoweredUDT` returns `nullptr` for a
struct with an embedded object (`HLLowerUDT.cpp:67`, and `:72` for the nested case);
`ScalarReplAggregatesHLSL.cpp:426` does not check it; `Ty != NewTy` is therefore true and the
null reaches `WrapInArrayTypes` at `:436`, which is where the assert fires. With `NDEBUG` that
assert is compiled out (`DXASSERT_NOMSG` → no-op) and the null type flows on to
`Builder.CreateAlloca(NewTy, ...)` at `:450` — hence the read from address 0 in the releases.

**It is not `Texture2D`-specific, and nesting does not avoid it.** A `SamplerState` payload
asserts identically, as does a `Texture2D` one level down inside a nested struct — the latter
through `GetLoweredUDT`'s recursive `return nullptr` at `HLLowerUDT.cpp:72`. The check that
rejects the field is `dxilutil::IsHLSLObjectType`. Replacing the member with a `uint` compiles
cleanly on `main` and on both ends of the release range (v1.5.2010, v1.9.2607).

**It is specific to `DispatchMesh`.** `IsPtrUsedByLoweredFn` (`ScalarReplAggregatesHLSL.cpp:310`)
recognises only `IOP_DispatchMesh`'s payload operand; the `TraceRay`, `ReportHit` and
`CallShader` cases sit next to it commented out under a `TODO: Lower these as well`. Nothing
else reaches the unchecked `GetLoweredUDT` call through this path today; enabling those three
would.

**On the "other AS related issue", [#3251](https://github.com/microsoft/DirectXShaderCompiler/issues/3251)
— related, not a duplicate.** Its repro still traps on `main` too (exit `0x80000003`), but in a
different assert in a different pass: `TranslateCBAddressUserLegacy` (`HLOperationLower.cpp`),
reached from `DxilGenerationPass`, not `WrapInArrayTypes` from `SROA_Parameter_HLSL`. Its payload
holds no HLSL object type, so `GetLoweredUDT` never returns `nullptr` and this issue's path is
never entered. Fixing this one will not fix that one.

Suggested label: add **`incorrect-code`** ("Issues relating to handling of incorrect code") —
the input is invalid HLSL that should be diagnosed, and the defect is that it crashes instead.
`bug`, `dxil` and `crash` all still fit.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
