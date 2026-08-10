> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3414](https://github.com/microsoft/DirectXShaderCompiler/issues/3414).

This is fixed. A local Debug build of `main` at `13730886e` compiles the shader from the
report correctly, as does every stable release from **v1.8.2505** (2025-05) onward.

**What was wrong.** `TraceRay(..., ray, payload)` passes the closest-hit shader's own `inout`
payload, which needs copy-in/copy-out. From **v1.6.2104** to **v1.8.2502** DXC instead handed
`dx.op.traceRay` the caller's payload object itself — the parameter and the operand are the
same value:

```llvm
; v1.8.2502, -T lib_6_3
define void @"\01?main@@..."(%struct.Payload* noalias %payload, ...) {
  call void @dx.op.traceRay.struct.Payload(i32 157, ..., %struct.Payload* %payload)
```

v1.8.2505 and `main` emit a distinct temporary, written before the call and read back after:

```llvm
; v1.8.2505, same command — identical register numbering on main
  %34 = getelementptr inbounds %struct.Payload, %struct.Payload* %2, i32 0, i32 0
  store <4 x i32> %20, <4 x i32>* %34, align 8
  call void @dx.op.traceRay.struct.Payload(i32 157, ..., %struct.Payload* nonnull %2)
  %35 = load <4 x i32>, <4 x i32>* %34, align 8
```

All four side by side: https://godbolt.org/z/9vKr9a34K

**Why the two variants in the report behaved differently.** The copy used to be generated
inside SROA's rewrite of alloca values (`RewriteCallArg(CI,
HLOperandIndex::kTraceRayPayLoadOpIdx, ...)` in `ScalarReplAggregatesHLSL.cpp`). The
workaround's `Payload new_payload` is an alloca, so it got one; the incoming payload is a
pointer parameter, so it did not. Compiled on v1.6.2104, the workaround's `dx.op.traceRay`
receives `%2` and the filed version receives `%payload`.

**On the 2023-07-14 question** — both halves of that observation hold on the affected builds:
the module does contain a store to the payload (`store <4 x i32> %19, <4 x i32>* %6` on
v1.7.2308), *and* it passes `%payload` to `dx.op.traceRay`. The store was not where the
problem was.

**History** — 20 stable releases, linear scan, no unusable probes:

| | |
| --- | --- |
| clean | v1.4.1907, v1.5.2010 |
| reproduces | v1.6.2104 … v1.8.2502 (13 consecutive releases) |
| clean | v1.8.2505 … v1.9.2607 |

The likely fix is `053e7ac65` ("Refactor udt intrinsic arg copy to before SROA, flatten
RayDesc", #7440): it moves UDT copy-in/copy-out out of SROA into an unconditional pre-pass and
adds `traceray_scalarrepl.ll`, which checks exactly the payload-as-pointer-parameter case. It
is in v1.8.2505 and not in v1.8.2502. The window is 162 commits, so treat this as strong
rather than certain. That PR was written for #7434 and does not reference this issue, which is
probably why it stayed open.

Nothing here was executed on a GPU; the evidence is the emitted DXIL.

Suggested labels alongside `bug`: `correctness`, `dxil`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
