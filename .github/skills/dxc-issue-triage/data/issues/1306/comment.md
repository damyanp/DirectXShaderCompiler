> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1306](https://github.com/microsoft/DirectXShaderCompiler/issues/1306).

On `main` (1.9.0.15422, `eff900d5`), DXC still accepts a barrier in divergent control flow
with no diagnostic. Unchanged from v1.4.1907 through v1.9.2607.

Repro: https://godbolt.org/z/c3ojha8KW

FXC rejects the original shader:

```
error X3663: thread sync operation found in varying flow control, consider reformulating your
algorithm so all threads will hit the sync simultaneously
```

DXC 1.6.2112 and trunk place the barrier inside the divergent branch (debug metadata elided):

```llvm
  %5 = icmp eq i32 %4, 0                     ; line:8 col:21
  br i1 %5, label %6, label %13              ; line:8 col:8

; <label>:6
  call void @dx.op.barrier(i32 80, i32 9)    ; line:10 col:9  Barrier(barrierMode)
```

The thread's conclusion still holds: without uniformity analysis the best achievable result is
a warning with false positives rather than an error, and the likely home for that analysis is
Clang (microsoft/hlsl-specs#246). Worth noting the link's fourth pane: Clang trunk compiles
this silently too, so the gap is not yet closed there either. Consider tracking it as a Clang /
HLSL specs item rather than an open DXC issue — but the repro is good and the gap is real, so
not as "cannot reproduce".

**Labels:** suggest adding `fxc-disagrees` and `diagnostic`, and removing `validation` — that
label means DXIL validation, whereas this is a front-end compile-time analysis. The only
validator discussed in the thread is SPIR-V's, which is a different component.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
