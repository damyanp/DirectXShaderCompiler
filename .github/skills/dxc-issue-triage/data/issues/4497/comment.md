> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4497](https://github.com/microsoft/DirectXShaderCompiler/issues/4497).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`), unchanged, and on **every** stable
release back to v1.4.1907 (2019). Compiler Explorer, annotated:
<https://godbolt.org/z/acfEvEz6o>

`-T ps_6_0 -E test1` — the `.f32` load is above the branch, and the two `[branch]` ifs are
folded into one:

```llvm
  %2 = call %dx.types.ResRet.f32 @dx.op.bufferLoad.f32(i32 68, %dx.types.Handle %1, i32 0, i32 0)
  %4 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 0, i32 12)
  %8 = and i1 %7, %6
  br i1 %8, label %9, label %10, !dx.controlflow.hints !10
```

`-E test2`, same file — the `.f32` load is inside the guarded block:

```llvm
  br i1 %4, label %5, label %10, !dx.controlflow.hints !10
; <label>:5
  %6 = call %dx.types.ResRet.f32 @dx.op.bufferLoad.f32(i32 68, %dx.types.Handle %1, i32 0, i32 0)
```

Both entry points were run on all 20 stable releases plus a Debug build of `main`: `test1`
hoists and `test2` does not, on all 21 builds. The asymmetry has never behaved differently, so
there is nothing to bisect and nothing in the report has gone stale.

**tex3d's 2022 analysis holds, and `-fcgl` shows it directly.** Before any pass runs, the front
end emits the whole-struct copy-in in the entry block:

```llvm
  %0 = alloca %struct.SData
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* %5, i8* %6, i64 32, i32 1, i1 false)
  call void @"\01?fct1@@YAXUSData@@@Z"(%struct.SData* %0)
```

Nothing hoists the load — it is unconditional from the first IR, and the optimizer only
narrows it (`value2` is dead, so what survives is `value.xyz` and `type`). A plain local
`SData data = dataBuffer[0];` with no function call behaves identically, so this is
whole-struct copy semantics rather than argument passing specifically.

The flattening is a consequence, not a second issue. DXC's `simplifycfg` does honour
`[branch]`, but only in two of the three flattening paths: `SpeculativelyExecuteBB`
(`SimplifyCFG.cpp:1494`) and `FoldTwoEntryPHINode` (`:1929`) both bail out on
`HasControlFlowHintToPreventFlatten`. The transform that actually fires here —
`FoldBranchToCommonDest` (`:2095`, which is what names the merged condition `%or.cond` at
`:2275`) — has no such guard. And it is legal here only *because* of the copy-in: it requires
everything ahead of the condition to be speculatable (`:2152`), which holds in `test1` where
the load is already in the entry block, and fails in `test2` where the load is inside the
guarded block. This matches the two follow-ups tex3d listed in 2022.

**The successor compiler reproduces the same asymmetry** (last two panes of the link,
`select i1 %5, i1 %8, i1 false` above a single branch for the by-value form). Those panes
compile a compute restating of the repro, because clang-dxc rejects `discard` today; the
restating was checked to still show the difference before it was published.

Label suggestion: keep `performance`, add `enhancement` — the input is valid, the output is
correct, and what is tracked here is two optimizer improvements rather than a defect. Not
suggesting `check-in-clang`, since the comparison above answers it.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
