> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3439](https://github.com/microsoft/DirectXShaderCompiler/issues/3439).

**Still reproduces on `main` (1.9.0.5433, `13730886e`)**, verbatim, from the repro as filed:

```
$ dxc -T ps_6_0 -E main repro.hlsl
error: External function used in non-library profile: \01?CallMeMaybe@@YAHM_N@Z
```

Checked every stable release that can be probed — **v1.4.1907 through v1.9.2607, 20 releases,
all mangled**. Never fixed, never regressed, never partially improved. Nothing in the issue text
is stale.

### There is already a demangler in tree, and this path doesn't call it

That seems like the actionable part. The diagnostic is emitted at
[`CGHLSLMSFinishCodeGen.cpp:3405`](https://github.com/microsoft/DirectXShaderCompiler/blob/main/tools/clang/lib/CodeGen/CGHLSLMSFinishCodeGen.cpp),
which formats the name with `dxilutil::PrintEscapedString(f.getName(), os)` — the raw
`llvm::Function` name, escaped but not demangled. Meanwhile `hlsl::dxilutil::DemangleFunctionName`
already exists (`include/dxc/DXIL/DxilUtil.h:117`, `lib/DXIL/DxilUtil.cpp:145`) and is already
called from `DxilContainerAssembler.cpp`, `DxcPixLiveVariables.cpp` and `DxilExportMap.cpp`.

It was added in `47958a941` (2018-02-12); this diagnostic was added in `4ade2fccc` (2018-06-20),
four months later, and the wording hasn't changed since.

One caveat so this isn't oversold: `DemangleFunctionName` recovers the bare name (`CallMeMaybe`),
not a signature — so it wouldn't distinguish overloads, which is the reason a mangled name is
useful in the first place. @llvm-beanz's suggestion above (move the diagnostic to Sema where the
AST name is available) is what would actually produce a readable signature. Calling the demangler
looks like the small fix available today; moving it to Sema is the real one.

### It's more than one message, and it's partial

Two other mangled diagnostics, both reproduced:

```
$ dxc -T lib_6_3 case-export-resource.hlsl
error: Exported function \01?TakesAResource@@YA?AV?$vector@M$03@@V?$Texture2D@V?$vector@M$03@@@@V?$vector@I$01@@@Z must not contain a resource in parameter or return type.
```

```
$ dxl -T ps_6_3 -E main link.dxil -Fo linked.dxil
error: Cannot find definition of function ?NotDefinedAnywhere@@YA?AV?$vector@M$03@@V1@I@Z
```

The first is `ReportDisallowedTypeInExportParam` (`CGHLSLMSFinishCodeGen.cpp:3233`), same shape.
The second is the linker (`DxilLinker.cpp:401`), and notably it *isn't* escaped — no `\01` — so
these sites each format the name their own way and a fix at one shared helper won't cover them.
The linker case also reproduces on all 20 releases.

But it genuinely is partial, and I'd rather say so than claim every message is affected. A DXIL
validator error naming a library entry point comes out fine:

```
error: For amplification shader with entry 'AmplifyWithHugePayload', payload size 32768 is greater than maximum size of 16384 bytes.
```

Entry points keep unmangled names. Reading `DxilValidation.cpp`, most rules do pass raw
`F->getName()`, so a non-entry function inside a library should still be mangled there — but I
didn't manage to construct an input that trips one of those rules on a non-entry function, so
treat that as a source reading rather than a result.

The reason this is a defect and not just taste: the same compiler, on the same function, in the
same run shape, gets it right when the diagnostic comes from Sema —

```
$ dxc -T ps_6_0 -E main control-redefinition.hlsl
error: redefinition of 'CallMeMaybe'
```

### Compiler Explorer

<https://godbolt.org/z/e6xsGc8YE> — DXC 1.6.2112 and trunk, both exit 5 with the mangled error.
The source there is a compute restatement of the pixel shader, because the third pane is
`hlsl_clang_trunk` and its backend can't lower a PS that writes a render target; DXC emits the
same message for both spellings. The `dxl` case above isn't shareable there — CE is single-file.

On the Clang pane, in case it's useful for the HLSL-in-Clang work: it **exits 0**. It accepts the
shader, lowers it, and emits `declare !dbg !111 internal i32 @_Z11CallMeMaybefb(float, i1)` — an
undefined declaration, with no diagnostic at all. So this isn't something the rewrite has already
solved; today it doesn't report the condition. I checked that isn't just an artifact of how CE
invokes it — the redefinition control above errors and exits 1 on the same pane
(<https://godbolt.org/z/EPczds3xM>). CE does run that pane in assembly-listing mode rather than
producing a validated container, so a later stage might still object.

**Suggested labels:** add `diagnostic` ("Issues for diagnostics"). Keep `enhancement` and
`tech-debt`. Not suggesting `validation` (that's DXIL validation specifically, and the one
validator message here is correct) or `shader-linking` (the linker instance is real, but the
issue's subject is the CodeGen message).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
