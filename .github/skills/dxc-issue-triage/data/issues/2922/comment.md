> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2922](https://github.com/microsoft/DirectXShaderCompiler/issues/2922).

**This no longer reproduces.** It was fixed between **v1.6.2112 and v1.7.2207**; the evidence
points to
[c0676c7ca](https://github.com/microsoft/DirectXShaderCompiler/commit/c0676c7ca1033a0e5c7a0b19caac6c42889b5b27)
("Handling dbg.value pointer case in O1.", #4375, Apr 2022). Verified on `main` @ `13730886e`.

@damyanp — no, this does not need tracking.

The repro as written can't be followed any more: `PixStructAnnotation_*` already runs at both
levels unconditionally, via

```c++
static const OptimizationChoice OptimizationChoices[] = {
    {L"-Od", false},
    {L"-O1", true},
};
```

and the same commit deleted all three of

```c++
break; // don't run -O1 test until pointer types are dealt with by value-to-declare pass
```

(those opt-outs were added in Dec 2020, after this was filed). Running the tests as filed:

```
$ TE.exe ClangHLSLTests.dll /name:PixTest::PixStructAnnotation_*
Summary: Total=18, Passed=18, Failed=0, Blocked=0, Not Run=0, Skipped=0
```

Because tests and fix landed together, I also ran each release's *own*
`-dxil-dbg-value-to-dbg-declare` over `PixStructAnnotation_FloatN`'s shader, via
`dxopt -external <that release>/dxcompiler.dll`. Counting `llvm.dbg.declare` instructions the
pass emits at `-O1` (what `PixTest` walks to build `AllocaWrites`):

| release | `llvm.dbg.declare` emitted |
| --- | --- |
| v1.6.2104, v1.6.2106, v1.6.2112 | **0** — variable dropped |
| v1.7.2207 … v1.9.2607, and `main` | 2 |

All 19 of those builds saw the same input: `call void @llvm.dbg.value(metadata
%struct.smallPayload.0* %p1, ...)` — the pointer case. v1.4.1907 (no `as_6_5`) and v1.5.2010
(emits no `DILocalVariable` at all) can't reach the pass, so they're not evidence either way.

Main's output contains `%4 = load %struct.smallPayload.0, %struct.smallPayload.0* %p1` — the
`B.CreateLoad(V)` that commit added — and v1.6.2112's does not, so the fix is executing rather
than merely present. The v1.6.2112 → v1.7.2207 window holds 248 commits, three of them touching
`DxilDbgValueToDbgDeclare.cpp`, so the attribution is strong rather than proven.

[Compiler Explorer](https://godbolt.org/z/End684Ycq) — DXC 1.6.2112 `-O1`, trunk `-O1`, trunk
`-Od`. CE cannot run the PIX pass, so the link shows only the pointer-typed `dbg.value` that
triggers it, against `-Od`'s `dbg.declare`.

**Suggested action: close as fixed.** Suggested labels: `PIX`, `bug`, `debug info` (the issue
currently has none).

The pass still returns early when a pointer-typed `dbg.value` is not an `AllocaInst`
(`// We only know how to handle AllocaInsts for now`). I did not test whether any shader
reaches that path.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
