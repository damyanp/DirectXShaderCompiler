> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4384](https://github.com/microsoft/DirectXShaderCompiler/issues/4384).

Still reproduces on `main` (built at `13730886e`) and on all 20 stable releases from v1.4.1907
(2019-07) to v1.9.2607, so it predates the report rather than regressing into it. Confirmed on
DXIL as well as SPIR-V, per @llvm-beanz's note.

```hlsl
enum EE : uint3 {
    E = uint3(0,0,0),
};
[numthreads(1,1,1)] void main() {}
```

```
$ dxc -T cs_6_0 -E main repro.hlsl
Internal Compiler error: unknown conversion kind
UNREACHABLE executed at <build root>\tools\clang\lib\Sema\SemaOverload.cpp:5154!
```

(only the build root is elided above; everything else is verbatim.) The entry point is
incidental: the two-line snippet alone fails identically. The filed SPIR-V/`-O3`/`-Zpc`
flag set and explicit `-HV 2021` and `-HV 2018` variants also fail identically.

The crash presents differently across that history, which matters if anyone writes a test for
it: v1.4.1907 and v1.5.2010 access-violate with **empty stderr**, v1.6.2104 exits `0xE0000002`
with `LLVM Unreachable`, and v1.6.2106 onward exits `0x80AA001C` with the message above.
@Ipotrick's "reading illegal memory address, address varies from run to run" matches the oldest
two; current builds fail deterministically. Compiler Explorer's Linux Release builds `SIGSEGV`,
so this is not Debug-only — `llvm_unreachable` is `#if 1` in
`include/llvm/Support/ErrorHandling.h`.

**DXC already computes the error @pow2clk asked for, then throws it away.** Stepping over the
throw in a debugger shows what was in the diagnostic buffer at that moment:

```
repro.hlsl:1:11: error: non-integral type 'uint3' is an invalid underlying type
repro.hlsl:2:9: error: enumerator value is not a constant expression
```

The same shader with a scalar enumerator — `enum EE : uint3 { E = 0, };` — prints that first
error normally, on all 20 releases and on `main`. So the base-type check has been correct since
at least 2019; what is missing is only that an internal error discards every diagnostic
produced before it.

Root cause: `Sema::CheckEnumConstant` → `CheckConvertedConstantConversions`
(`SemaOverload.cpp:5101-5154`) switches over `SCS.Second`, and the five HLSL-specific
conversion kinds (`Overload.h:94-101`) are not listed, so they reach the closing
`llvm_unreachable("unknown conversion kind")`. Here `SCS.Second` is `ICK_HLSLVector_Truncation`
— `uint3(0,0,0)` truncated to the `int` the enum recovered to after `uint3` was rejected.

`hlsl_clang_trunk` already gets this right, with the same arguments:
`error: non-integral type 'uint3' (aka 'vector<uint, 3>') is an invalid underlying type`, plus
a `-Wconversion` warning on the enumerator, and no crash. Repro and both DXC panes:
https://godbolt.org/z/rMsGE4K4s

`tools/clang/test/SemaHLSL/enums.hlsl` already covers `half`, `float`, `double`, `min16float`
and `min10float` underlying types with that diagnostic, but has no vector case.

Label suggestions: add **`diagnostic`**, and consider removing **`hlsl2021`** — the crash is
language-version independent (identical at `-HV 2018` and `-HV 2021` on `main`, and present on
v1.4.1907, whose default predates HLSL 2021; DXC's own enum tests run at `-HV 2017`). The label
may reflect thread history not visible here.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
