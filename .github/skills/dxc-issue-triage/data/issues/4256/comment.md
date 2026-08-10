> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4256](https://github.com/microsoft/DirectXShaderCompiler/issues/4256).

Still accurate. The validator does not recompute the ViewID state, on `main`
(1.9.0.5433, 13730886e) or on any shipped `dxv.exe` back to v1.8.2502 — the six
stable releases that ship the tool at all (v1.8.2502, v1.8.2505, v1.8.2505.1,
v1.9.2602, v1.9.2602.24, v1.9.2607).

`createComputeViewIdStatePass()` has three call sites — `PassManagerBuilder.cpp:391`
and `:709` (the compile pipeline) and `DxilLinker.cpp:1293`. None is in
`lib/DxilValidation/`, so validation has nothing to compare the serialized state
against.

Measured with `dxv.exe` over hand-edited modules built from one `vs_6_1` shader that
reads `SV_ViewID`. DXC computes `[8, 8, 15, 1, 2, 4, 8, 16, 32, 64, 128]` for it —
outputs 0-3 depend on ViewID, input *i* feeds output *i*. Deleting `!dx.viewIdState`
entirely, zeroing the dependency words, and replacing them with a deliberately false
mapping all pass. False mapping (the `[selftest]` lines are printed by the harness
that reads the module, before `dxv` runs):

```
[module] wrongdeps.ll (5990 bytes)
[selftest] module-calls-viewid-op=yes
[selftest] module-viewid-state=[8, 8, 240, 128, 64, 32, 16, 8, 4, 2, 1]
[selftest] module-viewid-state-declares-dependencies=yes
$ dxv.exe wrongdeps.ll
--- stdout ---
Validation succeeded.
[exit] 0x00000000
```

The same modules with an out-of-range `storeOutput` signature id, or with the shader
model lowered to 6.0, are rejected on every one of those validators — including
`error: Opcode ViewID not valid in shader model vs_6_0` quoting the `dx.op.viewID`
call. The validator reads the op; it just never checks it against the state.

**What has changed since 2022**, and why it does not close this: #6859 added
`PSVContentVerifier::VerifyViewIDDependence`, which does compare ViewID state during
validation. But it compares the PSV0 part with `DM.GetSerializedViewIdState()`
(`DxilContainerValidation.cpp:222`) — two copies of the same unvalidated metadata,
both derived from what the producer wrote — and returns early when the module state
is empty and the PSV state is all zero (`:225-229`). A producer that omits the node
gets both sides empty/zero and passes. What *is* recomputed is the `UsesViewID`
shader flag (`:504`), not the dependency data.

Suggested labels: **enhancement** (the ask is for validation the validator has never
performed) and **validation**. Whether the validator should own this is a product
decision — the pass exists and is already run during compilation and linking, so the
question is cost and where in `ValidateDxilModule` it belongs, not feasibility.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
