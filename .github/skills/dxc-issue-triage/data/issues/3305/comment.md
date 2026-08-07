> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3305](https://github.com/microsoft/DirectXShaderCompiler/issues/3305).

Still reproduces on `main` (`1.9.0.5433`, `ab5400907`), and on all 20 releases from v1.4.1907
(2019-07) through v1.9.2607 — the same DXIL message at the same location on every one, so this
predates the report rather than having regressed into it. The SPIR-V half of the same probe
succeeds on 19 of those 20 (every release that has SPIR-V codegen at all; v1.4.1907 does not).

Both back ends, same source, `-T lib_6_3`
([Compiler Explorer](https://godbolt.org/z/Pr3cfczY7)):

```
$ dxc -T lib_6_3 repro.hlsl
repro.hlsl:2:23: error: shader must include inout payload structure parameter.
[shader("miss")] void main(inout Payload payload) {}
                      ^

$ dxc -T lib_6_3 -spirv -fspv-target-env=vulkan1.2 repro.hlsl        # exit 0
    %Payload = OpTypeStruct
%_ptr_IncomingRayPayloadKHR_Payload = OpTypePointer IncomingRayPayloadKHR %Payload
```

(The SPIR-V half needs an explicit target environment — raytracing is gated on it, on `main` and
on v1.5.2010 alike — so a bare `-spirv` stops at that gate rather than on the payload. Not part
of this defect.)

## The DXIL error misnames its own cause

The shader *does* include an inout payload structure parameter. What DXC actually checked is
the payload's **size** — `CGHLSLMS.cpp:2492`, `if (0 == funcProps->ShaderProps.Ray.payloadSizeInBytes)`.
Two consequences worth knowing before anyone tries to fix this:

- A payload whose only member is itself an empty struct (`struct Inner {}; struct Payload { Inner i; };`)
  gets the identical message, so the trigger is zero size, not an empty outer struct.
- A *genuinely* missing payload parameter no longer produces this message — measured for `miss`
  on v1.7.2212 vs v1.7.2308, either side of #5131 (`f90af4e15`, 2023-04), which moved that case
  to Sema:
  `error: incorrect number of entry parameters for raytracing stage 'miss': 0 parameter(s) provided, expected one payload parameter`.
  The codegen message was accurate before then; today, for `miss`, the only input that reaches
  it is the one the words do not describe.

## What we think needs deciding

Whether an empty payload should compile for DXIL is a language/product call, not something the
current behaviour settles. The rejection is deliberate — it dates to
[`6e6f8dbd`](https://github.com/microsoft/DirectXShaderCompiler/commit/6e6f8dbdf) (2018),
"Require payload/attribute/param structs for ray shaders" — and DXIL validation has no lower
bound on payload size, so the rule lives entirely in the front end. On the SPIR-V side the
zero-member `OpTypeStruct` passes DXC's own spirv-val run. @damyanp's 2024-04-11 question about
the motivating scenario is still the thing this is blocked on.

The diagnostic, though, is wrong whichever way that goes: if empty payloads stay illegal the
message should say the payload is empty, and if they become legal the check goes away.

**Labels:** keep `bug`; suggest adding `diagnostic` for the misleading message. Not `spirv` —
as established in this thread, the SPIR-V path is the one that works.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
