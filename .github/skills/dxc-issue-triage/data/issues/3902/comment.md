> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3902](https://github.com/microsoft/DirectXShaderCompiler/issues/3902).

Still reproduces on `main` (1.9.0.5433, 13730886e). An unused `RayQuery` local is enough on its
own — no acceleration structure, no `TraceRayInline`:

```
$ dxc -T cs_6_5 -E computeRTAO repro.hlsl
error: validation errors
error: Flags must match usage.
note: Flags declared=33554432, actual=0
Validation failed.
```

Same result with the `/O3 /Ges /WX /all_resources_bound` command line as filed at `cs_6_6`, and
with both `ps_6_6` shaders from the later comments.

https://godbolt.org/z/1bWP3sov6 — 1.6.2112 and trunk both fail; the third pane is the same source
with the `RayQuery` uses restored, and compiles.

Every stable release that has `RayQuery` at all behaves this way: v1.5.2010 through v1.9.2607, 19
releases, no exceptions. v1.4.1907 predates both `RayQuery` and SM 6.5, so there is no release
without this.

Three additional findings:

- **The template ray flags are irrelevant.** An unused `RayQuery<RAY_FLAG_NONE>` fails identically.
  `33554432` is the raw shader-flag bit for raytracing tier 1.1, not an encoding of the ray flags.
- **`-Od` does not help**, so "the optimizer removes it" is not the whole story.
  `DxilFinalizeModule` calls `CollectShaderFlagsForModule()`
  ([DxilPreparePasses.cpp:1001](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/HLSL/DxilPreparePasses.cpp#L1001))
  *before* `RemoveUnusedRayQuery()` (line 1012), at every optimization level; the validator then
  recomputes from the final IR
  ([DxilValidation.cpp:4881](https://github.com/microsoft/DirectXShaderCompiler/blob/13730886e/lib/DxilValidation/DxilValidation.cpp#L4881))
  and gets 0. With `-Vd` the module shows both halves at once — `define void @computeRTAO() { ret
  void }` next to `!5 = !{i32 0, i64 33554432, ...}`.
- **`-validator-version 1.7` compiles cleanly.** `ValidateShaderFlags` carries a compatibility
  shim for validator versions ≥1.5 and <1.8 that suppresses exactly this mismatch. It is a
  workaround for anyone blocked today, at the cost of pinning to an older validator.

Suggested label: `validation`, since DXC emits a module whose declared feature flags its own
validator rejects.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
