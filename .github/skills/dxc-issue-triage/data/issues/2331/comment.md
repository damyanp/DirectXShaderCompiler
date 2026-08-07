> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2331](https://github.com/microsoft/DirectXShaderCompiler/issues/2331).

**Still reproduces on `main` (1.9.0.5433, `ab5400907`).**

```
$ dxc -T ps_6_0 -E MainPS repro.hlsl
error: validation errors
repro.hlsl:24:1: error: Instructions must be of an allowed type.
note: at 'unreachable' in block '#4' of function 'MainPS'.
Validation failed.
```

Compiler Explorer, unmodified body repro: **https://godbolt.org/z/nEqsn9nEW**

@tristanlabelle's 2019 diagnosis still holds: `-Vd` shows the fall-off path becoming
`unreachable`. `utils/hct/hctdb.py` marks `Unreachable` disallowed in
`mark_disallowed_operations`; the generated `IsLLVMInstructionAllowed()` is checked in
`lib/DxilValidation/DxilValidation.cpp` before `ValidationRule::InstrAllowed` is emitted.

**Signing is not involved.** The report's `DXIL.dll not found` warning is environmental
(shader-playground shipped no `dxil.dll`); validation runs either way and fails here, so nothing
reaches signing. Since the external validation paths were removed from `dxcompiler.dll`, current
builds do not consult a sibling `dxil.dll` at all, and valid containers are signed without one.

**Two claims in the body no longer describe the compiler** — worth knowing, because someone
spot-checking them today could reasonably conclude the whole report is obsolete. It is not; only
these two have moved:

| body claim | today |
| --- | --- |
| comment out one `case` → "validates clean, but it shouldn't" | `error: control may reach end of non-void function [-Wreturn-type]` — the validator is never reached |
| add a fourth enumerator `Fake` → still a validation error | same front-end error |

Adding `default:` still compiles clean, as the body says.

Measured across all 20 releases from v1.4.1907: both changed between **v1.4.1907 and
v1.5.2010**. In source, `warn_maybe_falloff_nonvoid_function` gained `DefaultError` in
`8c43a1456`, *"Default to error on missing return from non-void function"* — in v1.5.2010,
not in v1.4.1907. (434 commits in that window, so: strong attribution, not a bisected one.)

That is the fourth bullet of tristanlabelle's list, delivered in 2020 — but only where the
front end can see the switch is non-exhaustive. **A switch covering every declared enumerator
still satisfies `-Wswitch`, passes Sema, and lands on the validator**, which is the whole of
what remains here. The repro's own `(::QualityT)(shaderKey & 3)` can yield `3`, so the
fall-off-the-end path is reachable — the point tristanlabelle made when he argued a
`default:` on an exhaustive enum switch is legitimate rather than redundant.

His first bullet has also largely been addressed: the error now carries a source location and
names the instruction, where in 2019 it printed only `at 0x24f9e5b2a10 inside block #0`.

On @llvm-beanz's 2024 note about removing these instructions during DXIL lowering in Clang:
clang cannot compile this shader as written, and a compute translation of it hits a backend
error that clang also produces for inputs DXC accepts, so neither says anything here. On a
cut-down restating of the construct, clang compiles it and emits no `unreachable` — the default
edge goes to the merge block and the undefined path contributes `poison` to the phis.

Nothing here disturbs the 2024 position that this won't be fixed in DXC; whether "dormant"
should mean closed is a call for the team.

**Suggested labels:** add `validation` ("Related to validation or signing" — this is a DXIL
validation failure) and `incorrect-code` (the shader is incorrect, and the complaint is that DXC
catches it in the validator rather than in Sema). Keep `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
