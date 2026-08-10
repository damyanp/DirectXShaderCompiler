> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3251](https://github.com/microsoft/DirectXShaderCompiler/issues/3251).

**Still reproduces on `main` (1.9.0.5433, `13730886e`), and on every release binary that supports
`as_6_5`.** The repro in the body works as filed; the assert is still the one named in the title,
still in `TranslateCBAddressUserLegacy`, still because the user is `HLOpcodeGroup::NotHL`.

```
$ dxc -T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug repro.hlsl
Internal compiler error: Terminal Error 0x80000003
```

That is all a plain run prints — the assert text goes to `OutputDebugString`. Under `cdb`:

```
Error:  !(0)
File:
Func:   `anonymous-namespace'::TranslateCBAddressUserLegacy.
        not implemented yet
```

(cdb leaves `File:` empty; in current source that `DXASSERT(0, "not implemented yet")` is
`lib/HLSL/HLOperationLower.cpp:8801`.) The stack reaches it as
`DxilGenerationPass::GenerateDxilOperations` → `TranslateHLSubscript`
(`CBufferSubscript`) → `TranslateCBOperationsLegacy` → `TranslateCBAddressUserLegacy`.

The line moved since the report. `HLOperationLower.cpp:6207` was then the `CallInst` arm's final
`else`. PR #3034 (`eaa7f95d0`, six days after this was filed) added an `IntrinsicInst` branch for
lifetime markers above it, and `llvm.memcpy` *is* an `IntrinsicInst`, so it now lands in that
branch's inner `else` at 8801 — textually identical to the outer one, now at 8804.

### The assert is not the whole defect

Every shipping release is a Release build, where `DXASSERT` is `do { } while (0)` — so it would
be easy to read "no release asserts" as "fixed". It is not. With the assert compiled out the
memcpy is left untranslated *and unerased*, and the pointer it uses is deleted anyway
(`BCI->eraseFromParent()` at 8845; `DXASSERT(CI->use_empty(), …); CI->eraseFromParent();` at
9920–9922, that guard also compiled out). LLVM's backstop
`assert(use_empty() && "Uses remain when a value is destroyed!")` is compiled out too. Continuing
past both asserts in a debugger — which runs what a release build runs — ends in an access
violation in `InstCombiner::visitCallInst` → `MemTransferInst::getSource`, dereferencing the
dangling operand.

So the release history is a real measurement, and it is uniform: **all 19 releases from
v1.5.2010 (2020-10) to v1.9.2607 fail.** v1.4.1907 is the only exception and it never ran the
repro — `error: invalid profile as_6_5`, confirmed with a minimal `DispatchMesh` shader. Since
v1.5.2010 predates this report by three weeks, that covers the issue's whole life.

The failure wears four different faces across those releases, which is worth knowing for anyone
matching on output: `Internal compiler error: access violation` (8), no output at all (1,
v1.5.2010), `DataLayout::getTypeSizeInBits(): Unsupported type` (9, split between
`DXC_E_LLVM_UNREACHABLE` and E_FAIL), and `llvm::cast<X>() argument of incompatible type!` (1,
v1.8.2403). Eight of the 19 exit with plain E_FAIL — the same status as a syntax error.

Compiler Explorer: **https://godbolt.org/z/arjrMWhWf** — `dxc_1_6_2112` and `dxc_trunk`, both
`SIGSEGV`. CE builds are Release, so the assert itself cannot appear there; the page shows the
post-`NDEBUG` consequence, and it corroborates the Debug build rather than standing in for it.

### Scope, and a workaround

Measured on `main`:

- **Not `$Globals`-specific.** Moving the global into an explicit `cbuffer MyCB : register(b0)`
  traps identically.
- **Not any memcpy out of a cbuffer.** The same whole-struct copy out of the cbuffer into an
  `RWStructuredBuffer` element in `cs_6_0` compiles cleanly (exit 0) — on the tested cases it is
  the `DispatchMesh` payload that keeps the copy as an `llvm.memcpy` into DXIL lowering.
- **Writing the copy field by field compiles cleanly** — on `main`, v1.5.2010 and v1.9.2607.
  That is a usable workaround today:

  ```hlsl
  p.lhSampleData.linearTerms[0] = g_lhSampleData.linearTerms[0];
  // ... etc, one field at a time
  ```

Labels: `bug` + `crash` are already right; no change suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
