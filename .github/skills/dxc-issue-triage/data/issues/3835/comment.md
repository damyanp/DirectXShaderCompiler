> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3835](https://github.com/microsoft/DirectXShaderCompiler/issues/3835).

**Still reproduces on `main` (1.9.0.5433, `13730886e`)**, and on every stable release from
**v1.4.1907 (2019-07) through v1.9.2607** — 20/20, linear sweep, no fix window.

Compiler Explorer, the shader exactly as filed: <https://godbolt.org/z/aYedzh96v>

The trigger is the incomplete array type in these two declarations:

```hlsl
float _expr13[] = perVertexStruct.gl_ClipDistance;
float _expr14[] = perVertexStruct.gl_CullDistance;
```

Give either an explicit bound and the shader compiles cleanly.

### The title is misleading

This is not a DXIL validation problem. DXC crashes in clang CodeGen, before there is any DXIL to
validate. An assert-enabled build stops at the assert tex3d identified:

```
Error: assert(!isIncompleteType() && "This doesn't make sense for incomplete types")
dxcompiler!clang::Type::isConstantSizeType
dxcompiler!clang::CodeGen::CodeGenFunction::EmitAutoVarAlloca
```

A release build has that assert compiled out and runs on into a null dereference — the reported
symptom. Running the debug binary with asserts stepped over reaches it in the same process, on
the same input, so these are demonstrably one defect and not two:

```
Access violation - code c0000005
dxcompiler!ConvertScalarOrVector
dxcompiler!AddMissingCastOpsInInitList
dxcompiler!CGMSHLSLRuntime::EmitHLSLInitListExpr
```

### The silent half is arguably worse than the crash

tex3d's 5-line repro doesn't crash a release build — it **compiles successfully and emits an
empty entry point** on all 20 releases. No load, no `storeOutput`, no diagnostic. Adding `[1]`
to the declaration produces correct code on every one of them.

Restated as a compute shader so the bad value reaches a UAV, `dxc_trunk` shows what actually
happened:

```
error: validation errors
error: Assignment of undefined values to UAV.
note: at 'call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 0, i32 undef, i32 undef, i32 undef, i32 undef, i32 undef, i8 15)'
```

The front end produced `undef` for every component. The validator is doing its job here; it is
catching DXC's own output.

### Both other compilers have already picked an answer, and they differ

- **FXC compiles the filed shader** (`/T vs_5_0 /E vert_main`, exit 0), confirming llvm-beanz's
  comment. On the reduced case its output is byte-identical to the explicitly-sized version
  (`store_uav_typed u0.xyzw, l(0,0,0,0), l(7,7,7,7)`) — it handles the form correctly, not just
  tolerantly.
- **Clang's HLSL front end rejects it**: `error: array initializer must be an initializer list`,
  on exactly those two lines (third pane in the link — its `SV_ClipDistance` errors are an
  unrelated gap). Controlled against a trivial shader and against the one-token sized variant,
  both of which compile clean.

So the language question tex3d raised is still open in DXC while the successor has already
chosen "diagnose and fail" and FXC has chosen "support it". That decision isn't triage's to
make, but whichever way it goes, crashing on one input and silently emitting an empty entry
point on another isn't a defensible outcome for either.

### Labels

Keep `bug`, `crash`, `incorrect-code` — all three are independently evidenced. Suggest adding
**`correctness`** (the silent empty entry point and the `undef` stores are wrong code, separate
from mishandling invalid input) and **`fxc-disagrees`** (measured above). Possibly
**`hlsl-next`**, since the open question is a language one. Not `validation`, despite the title:
the fault is in CodeGen.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
