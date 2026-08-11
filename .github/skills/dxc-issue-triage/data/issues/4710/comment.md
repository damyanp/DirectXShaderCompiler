> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4710](https://github.com/microsoft/DirectXShaderCompiler/issues/4710).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`), and it is a **regression**: v1.4.1907
compiles this shader; v1.5.2010 is the first release that rejects it, and every release since
does. The 20-release scan ran three positive controls on every binary.

```text
repro.hlsl:25:41: error: Index for resource array inside cbuffer must be a literal expression
```

v1.4.1907 emits handles at `t0`/`t5`/`t10`/`t15`, as the loop requires.
FXC `ps_5_0` independently produces the same binding layout; FXC `ps_5_1`
fails as described in the thread. All panes:
<https://godbolt.org/z/EKh5E8Y4M>.

**Why `[unroll]` cannot help.** The check is in a DXIL-lowering pass, not in Sema —
`HLModule::GetBindingForResourceInCB` (`lib/HLSL/HLModule.cpp:816`) rejects a GEP that
`!hasAllConstantIndices()`. `dxc -Odump` places `-dxilgen` at index 36 and
`-dxil-loop-unroll` at 41, so the guard runs before `[unroll]`; `-fcgl`
accepts the shader.

`git log -S` strongly points to `94460c988`, which introduced per-element
resource binding and rewrote `resource-in-cb4.hlsl` from a passing binding
table to an expected diagnostic. It is inside the 434-commit release window;
the exact commit was not built.

The remaining question is whether the guard is too strict or intentionally
rejects a binding model that cannot represent the pre-unroll index. The output
does not settle that design decision.

**Also worth a separate issue:** Clang trunk in DXC mode *crashes* on this shader in
`CGHLSLRuntime::emitBufferCopy`. The same shader with the resource member removed compiles
cleanly, so the crash tracks the resource-in-cbuffer copy specifically.

Suggested labels: `bug` (a measured regression), `diagnostic` (the symptom is the diagnostic
itself), `check-in-clang` (checked — it crashes, and that needs its own fix).

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
