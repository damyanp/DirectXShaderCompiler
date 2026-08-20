> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#5434](https://github.com/microsoft/DirectXShaderCompiler/issues/5434).

Still reproduces on `main` (1.9.0.5465, `89e2f98`): `AnnotateHandle`, `AnnotateNodeHandle`
and `AnnotateNodeRecordHandle` accept a handle operand that was never derived from any
`Create*Handle` call, and the validator raises nothing.

No HLSL repro is possible here — a normal compile always CodeGens a matching create/annotate
pair — so this is measured with hand-written DXIL fed straight to the standalone validator
(`dxv`), not Compiler Explorer:

```
$ dxv variant-annotatehandle-zero.ll
Validation succeeded.
```

Feeding the identical zero/undef handle to an ordinary checked opcode instead
(`BufferUpdateCounter`) is correctly rejected, so this isn't zero/undef handles being
silently accepted everywhere in the module — it's specific to these opcodes:

```
$ dxv control-bufferupdatecounter-zero.ll
error: Instructions should not read uninitialized value.
Validation failed.
```

`DxilValidation.cpp`'s `ValidateHandleArgs` still names the gap explicitly:

```cpp
case DXIL::OpCode::AnnotateHandle:
case DXIL::OpCode::AnnotateNodeHandle:
case DXIL::OpCode::AnnotateNodeRecordHandle:
case DXIL::OpCode::CreateHandleForLib:
  // TODO: add custom validation for these intrinsics
  break;
```

That TODO was added by #5399 (2023-07-21), three days after this issue was filed, as a
deliberate carve-out while implementing item 1 of #5356 for every other handle-consuming
opcode. It is unchanged today, and the same gap is present in the tested release (v1.8.2502)
as well as on `main` — this was never implemented rather than having regressed, so there's no
fixed-in/regressed-in release to point to.

Current labels (`enhancement`, `tech-debt`, `validation`) already describe this well; no
changes suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
