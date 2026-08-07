# Expected symptom — #3444 "[DXIL] Decorating CS float argument with SV_DispatchThreadID semantic crashes the compiler"

**Reported (2021-02-10):** a compute shader whose entry parameter is a **scalar** `float`
carrying `SV_DispatchThreadID` crashes DXC. The title states `float2`/`float3`/`float4` work.

**Repro quality:** `complete` — a full four-line compute shader.

**What we test:** compile as `cs_6_0`, entry `CSMain`.

**Symptom is present if:** DXC fails internally rather than compiling or diagnosing.

**Symptom is absent if:** DXC emits a clean diagnostic that the type is unsupported for this
semantic — which is the explicitly intended fix (see below) — or compiles it.

**This issue has a documented fix-and-revert history, so the history verdict matters more than
usual.** The sequence in the thread:

1. 2021-02 — @vcsharma: the compiler lacked type checking for SV semantics, causing "random
   crashes"; PR #3043 would turn these into a compile error.
2. 2023-09 — @pow2clk: "**Reverted change resurfaced this bug**."
3. 2024-07 — @damyanp: current DXC crashes with `error: cast<X>() argument of incompatible
   type!` — and, crucially, **"For float, float2, float3 and float4."**

So the expected history is `regressed`, not `always-repro'd`. Bisection should show the crash
absent in some middle range of releases and present at both ends. **This is the first issue in
this triage where the bisection search should actually do work** — batch 001 was entirely
`always-repro'd`, so the search path has never been exercised.

**The title is expected to be wrong.** It claims the vector types work. @damyanp reports all
four crash. Test `float`, `float2`, `float3` and `float4` separately and record each: if the
symptom has widened, that is a finding in its own right and means the title now misdescribes
the bug.

**Predicate care:** the reported failure is `cast<X>() argument of incompatible type!`, which
in a Release build escapes as E_FAIL. Use the `internal_failure` predicate, not text matching
— and note that E_FAIL alone is *not* sufficient (dxc returns it for ordinary errors too), so
the text marker is what distinguishes this case.

**Related:** the reporter notes the SPIR-V backend produces validation errors for the same
shader, tracked separately as #3443. Out of scope here.
