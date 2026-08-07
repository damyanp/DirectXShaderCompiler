> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1702](https://github.com/microsoft/DirectXShaderCompiler/issues/1702).

The reported assert no longer reproduces on `main` (1.9.0.15422, `eff900d5`), but the codegen
bug behind it does.

Repro: https://godbolt.org/z/Tfe5d4fGW

**The assert is absent from every release I can test.** `SROA_Helper::RewriteBitCast` does not
fire in any of the 20 releases from v1.4.1907 (2019-07) onward. That is the oldest release
shipping a usable `dxc.exe`, so this cannot establish when it stopped — only that it is gone
from everything checkable. Worth knowing before anyone re-tests this issue by looking for the
crash and concludes it is fixed.

**The bug it came from is still there.** DXC accepts the unsized parameter
`float4 Func(float4 a[])`, which FXC rejects with `error X3072: 'a': array dimensions of
function parameters must be explicit`. The argument then never reaches `Func`. In the linked
compute repro DXC emits undefined stores, and its own validator rejects the result:

```
error: Assignment of undefined values to UAV.
Validation failed.
```

The pixel shader from the issue has the same trigger but fails more quietly: the call is
dropped, `main` is empty, and the only hint is `warning: Declared output SV_Target0 not fully
written in shader`. v1.4.1907 produced that same empty `main`, without the warning. Giving the
parameter an explicit size (`float4 a[2]`) compiles cleanly and stores real values, which
isolates the unsized parameter as the trigger.

A 2024 comment above says this needs broader parameter-passing work that would likely be
addressed in Clang. Clang trunk already compiles the linked repro correctly, storing the real
values. So whichever answer is right for the language — reject it like FXC, or accept it like
Clang — DXC currently matches neither.

If the issue remains open, the title and description could focus on the codegen rather than the
reported assert.

**Labels:** suggest adding `fxc-disagrees`, `incorrect-code` and `correctness`, and removing
`shader-linking` — the repro is self-contained and I don't see a linking component in the
thread, though I may be missing why it was applied.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
