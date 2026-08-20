# Expected symptom

Issue: waterfall-loop pattern (`for(;;) { u = WaveReadLaneFirst(a); if (a==u) { <wave-sensitive
load>; break; } }`) compiles differently depending on shader stage.

The reporter shows that compiling as a **pixel shader** (`-T ps_6_0`) keeps the
`mainBuf[u][b]` buffer load *inside* the loop body, guarded by the `dx.break` mechanism
(added in PR #2795 to stop the optimizer from treating wave-op results as loop-invariant and
hoisting wave-sensitive work out of the loop). The generated DXIL/IR references a
`dx.break.cond` global and a `%dx.break()` conditional-branch pattern.

Compiling the **same source** as a **vertex shader** (`-T vs_6_0`) instead hoists the buffer
load (and its dependent `LoadInput`) out of the loop entirely — no `dx.break` machinery
appears anywhere in the VS output. The reporter (and a later comment from the same person,
quoting `CGHLSLMS.cpp`'s `EmitHLSLCondBreak`) attributes this to the fact that the function
only engages the `dx.break` conditional-branch mechanism for Pixel, Compute and Lib shader
models:

```cpp
if (!m_pHLModule->GetShaderModel()->IsPS() && !m_pHLModule->GetShaderModel()->IsCS() &&
    !m_pHLModule->GetShaderModel()->IsLib()) {
  return CGF.Builder.CreateBr(DestBB);   // plain unconditional branch, no dx.break
}
```

**"Reproduces" means:** compiling the reporter's `break.hlsl` for `vs_6_0` produces DXIL/IR
that contains no `dx.break` machinery (the wave-sensitive buffer load is not protected against
loop-invariant hoisting), while compiling the identical source for `ps_6_0` (or `cs_6_0`) does
contain `dx.break` machinery for the same construct. That contrast — VS lacks the protection
that PS/CS have for the *identical* source — is the reported bug, not merely "VS output looks
different".

**Repro quality:** `complete` — the issue body includes the exact HLSL source, the exact two
`dxc` command lines used (`/Tps_6_0 ... /DOUTPUT=SV_Target` and `/Tvs_6_0 ... /DOUTPUT=Z`), and
the exact IR emitted for both, so nothing needs to be reconstructed.

**Not compiler-verifiable:** N/A — this is fully answerable from `dxc` disassembly.
