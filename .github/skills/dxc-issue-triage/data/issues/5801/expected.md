# Expected symptom (written before running anything)

Issue: [#5801](https://github.com/microsoft/DirectXShaderCompiler/issues/5801) — "Sample immediate
offset range is not diagnosed or validated in SM 6.7"

**Reported behaviour:** compiling the repro shader below with `-T ps_6_7`, an out-of-range
immediate texture-sample offset (`int2(12, -14)`, outside the DXIL-legal `[-8, 7]`) produces
**no** front-end diagnostic and DXIL validation also emits **no** error. On `-T ps_6_6` and
earlier, the same source produces:

```
error: Offsets to texture access operations must be between -8 and 7.
```

The issue also attaches a standalone `.ll` module and a `%dxv` `RUN:` line asserting the DXIL
validator itself should reject an out-of-range offset with:

```
Function: main: error: offset texture instructions must take offset which can resolve to
integer literal in the range -8 to 7.
```

**"This reproduces" means:** compiling the repro at `-T ps_6_7 -E main` (or any SM 6.7+ profile)
with the constant out-of-range offset produces a clean compile (exit 0, no
`Offsets to texture access operations` / `InstrTextureOffset`-style diagnostic anywhere in the
output), while the same source at `-T ps_6_6 -E main` still produces the error. If SM 6.7+ also
emits the error, the bug is fixed (`does-not-repro`). If SM 6.6 stops emitting the error too,
that is a `changed-behavior` (the guard rail disappeared entirely, not just for 6.7+).

**Repro quality:** `complete` — the issue supplies a full, compilable HLSL source with the exact
offending call plus a self-contained pre-built DXIL `.ll` module for the validator half. Both are
used as filed, with `-E main` added for the HLSL half since the `RUN:` line relies on the test
harness's implicit default entry point.

**A second predicate is needed for the DXIL-only half:** the attached `.ll` exercises
`DxilValidation` directly through `%dxv`, independent of front-end codegen. This project's
`main-debug` compiler is `dxc.exe`, not a validator-only tool, so the `.ll` module is scored as a
`variant-*` control by disassembling/recompiling through the same `dxc` binary rather than a
separate `dxv` invocation (no `dxv.exe` is registered alongside `main-debug`).
