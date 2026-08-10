> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3906](https://github.com/microsoft/DirectXShaderCompiler/issues/3906).

Still reproduces. The shader in the report fails to compile on `main` (1.9.0.5433, `13730886e`)
and on **all 20 stable releases from v1.4.1907 to v1.9.2607** — it has never worked.

Live repro: **https://godbolt.org/z/M7Ex1s9b3** (the `shader-playground` link in the report no
longer resolves). Both DXC panes answer `Killed - processing time exceeded`. Locally, v1.9.2607
was still running after 600 s, at 100% CPU throughout — a spin, not a wait.

### One defect, two signatures

| build | `dxc -T cs_6_0 -E main` |
|---|---|
| Release (all 20 stable releases) | never terminates |
| Debug (`main`) | `0xE0000001`, `Internal compiler error: LLVM Assert`, ~1 s |

Under a debugger the Debug build stops in `SROA_Helper::RewriteBitCast`, and continuing past
that assert — which is what a Release build does, since the assert is not compiled in — reaches
a second one whose message names the reported symptom:

```
assert(0 && "Type mismatch.")           lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp(2662)
!(&TheUse != PrevUse)                   lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp(2996)
    Infinite loop while SROA'ing value, use isn't getting eliminated.
```

The bail-out at 2661-2663 returns without erasing the bitcast or nulling the use, breaking the
contract stated at 2999-3000 (*"Each of these must either call `->eraseFromParent()` or null out
the use of V so that we make progress"*), so `while (!V->use_empty())` at 2991 never advances.
Both guards are `NDEBUG`-only, so Release just spins. That bail-out dates to `6ee4074a4`, the
first commit in the repository, which matches the release scan.

### Reduced repro

No `ByteAddressBuffer`, no `register`, no `readIndex()`:

```hlsl
struct RenderResourceHandle { uint handle; };

struct Test {
    RenderResourceHandle h;
    float3 infLoop()[2] {
        uint i = this.h.handle;
        float3 v[2] = { 0.xxx, 0.xxx };
        return v;
    }
};

[numthreads(8, 8, 1)] void main() {
    Test t;
    t.h.handle = 0;
    float3 w[2] = t.infLoop();
}
```

Two variants measured on v1.6.2106, v1.9.2607, and `main`:

- Removing the struct member entirely (member function returning an array, but no data member)
  compiles cleanly — as does lifting the function out of the struct.
- Replacing `RenderResourceHandle h;` with `uint h;` gives a **different** failure, not a hang:
  `llvm::cast<X>() argument of incompatible type!`, from the neighbouring exit at
  `ScalarReplAggregatesHLSL.cpp(2630)`. Worth covering in the same fix's tests.

The workaround in the report (wrap the values in a struct and return the struct) still works —
`repro.hlsl` with only that change compiles on `main`, v1.6.2106 and v1.9.2607. The new
Clang-based HLSL front end (`hlsl_clang_trunk` on the link above) compiles all of these without
incident.

**Labels:** no change suggested — `bug` and `crash` already fit, and `crash` covers "hitting an
assert".

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
