> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5491](https://github.com/microsoft/DirectXShaderCompiler/issues/5491).

Still reproduces on `main` (built at the public commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`) and on every stable release checked back to
v1.4.1907 (2019-07) — this has never behaved differently. Compiler Explorer, both DXC's oldest
build and current trunk: <https://godbolt.org/z/1T6e4zWsf>

```llvm
define void @main() {
  %1 = call i32 @dx.op.loadInput.i32(i32 4, i32 0, i32 0, i8 0, i32 undef)
  %2 = call i32 @dx.op.waveReadLaneFirst.i32(i32 118, i32 %1)  ; WaveReadLaneFirst(value)
  ret void
}
```

`%2` is never referenced before `ret void` — the same shape reported in 2023.

**Why the call survives DCE:** `dx.op.waveReadLaneFirst` (like every wave/quad intrinsic in
`DxilOperations.cpp`) is declared with no `readnone`/`readonly` attribute, only `nounwind`
(visible in this build's own disassembly: `declare i32 @dx.op.waveReadLaneFirst.i32(i32, i32)
#1` / `attributes #1 = { nounwind }`). Ordinary LLVM DCE only removes an unused call to an
external function it can prove has no side effects, so a plain `nounwind` declaration is never
eligible, regardless of whether the caller uses the result.

That reads as deliberate conservatism rather than an oversight: a wave op's result depends on
which lanes are active at that program point, so treating it as an ordinary pure value that can
be freely deleted is not obviously safe in general — which is the same concern raised in this
thread already (*"I'm not convinced there isn't a correctness bug lurking here too"*). DXC does
have a separate mechanism that deletes a wave op when it can prove the surrounding control-flow
region is dead (`EraseDeadRegion`, exercised by
`wave_intrinsic_dead_loop.hlsl`), but that is a different, narrower proof than "this call's
result value happens to be unused," which is what this issue asks for. The linked PR #5559 is
unmerged and is itself a workaround for that other mechanism over-deleting a wave op it should
have kept — evidence the surrounding design space is still being worked out, not that this case
has been addressed.

No label change proposed — `bug`, `performance`, `dxil` already fit: a real, longstanding
missed optimisation rather than a correctness defect in what is currently emitted.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
