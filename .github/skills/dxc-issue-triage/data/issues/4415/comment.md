> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4415](https://github.com/microsoft/DirectXShaderCompiler/issues/4415).

Both asks still reproduce on `main` (1.9.0.5433, `13730886e`), unchanged since this was filed.

**The front-end half** is exactly as described: `-Wuninitialized` fires, the compile succeeds,
exit 0.

**The validator half** also holds, and the emitted instruction is still character-for-character
the one quoted above:

```
%1 = call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle zeroinitializer, %dx.types.ResourceProperties { i32 13, i32 4 })
```

Since the validator's job is to reject bad DXIL whatever produced it, this was also probed with
modules DXC never emitted — a valid module with the `annotateHandle` handle operand patched to
`zeroinitializer`, and again to `undef` — fed straight to `dxv`. Both: `Validation succeeded.`

The contrast that pins it down: **the same operand value on a different opcode is rejected by
name.**

```
$ dxv control-checkedop-zeroinit.ll
Function: main: error: Instructions should not read uninitialized value.
note: at '%3 = call %dx.types.ResRet.f32 @dx.op.textureLoad.f32(i32 66, %dx.types.Handle zeroinitializer, i32 0, i32 0, i32 0, i32 undef, i32 undef, i32 undef, i32 undef)' in block '#0' of function 'main'.
[3 further consequent errors elided]
Validation failed.
```

And corrupting the *props* operand of that very same `annotateHandle` call is rejected
(`Constant values must be in-range for operation.`), so the instruction is inspected — just
never its handle operand.

That matches the source. `ValidateHandleArgs()` in `lib/DxilValidation/DxilValidation.cpp`
routes `AnnotateHandle`, `AnnotateNodeHandle`, `AnnotateNodeRecordHandle` and
`CreateHandleForLib` to `break` under `// TODO: add custom validation for these intrinsics`;
every other opcode goes to `ValidateHandleArgsForInstruction()`, which raises
`InstrNoReadingUninitialized` for exactly this. That check landed in 9468120e6 (PR #5399,
2023-07-21) — after this issue — and excluded `AnnotateHandle` from the start.

**Not just this build**: pointing `dxv` at the signed `dxil.dll` from the v1.8.2505.1 release
archive (1.8.2505.32) gives the same split — the `textureLoad` module rejected, the
`annotateHandle` module accepted. Across releases, every one that can compile the repro
(v1.6.2112 through v1.9.2607) accepts it, and all six that ship `dxv.exe` accept the doctored
module too. The two SM 6.6 preview releases (v1.6.2104/2106) reject it, but only incidentally —
they lower `ResourceDescriptorHeap` to `createHandleForLib` and trip
`opcode 'CreateHandleForLib' should only be used in 'Library'`, not any handle rule.

<https://godbolt.org/z/156dMcvPv> — dxc 1.6.2112 and trunk, both emitting the instruction.

Labels `bug` + `validation` look right as they stand.
The front-end question — whether the warning should become an error by default — is a
product decision rather than a triage one.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
