> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5039](https://github.com/microsoft/DirectXShaderCompiler/issues/5039).

Still reproduces on `main` (public commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df);
the local build self-reports a different, fork-local commit,
`1.9.0.5465 (triage, 7665270b9)`, but its source tree is identical to
`89e2f98e2`), and on every stable release checked, v1.4.1907 through
v1.9.2607. This has never been fixed — only reworded.

**Compiler Explorer:** https://godbolt.org/z/aM54EnbzT

```
$ dxc -T ps_6_0 repro.hlsl
error: llvm::cast<X>() argument of incompatible type!
```

That matches the text quoted in the report on current builds. The wording
*has* drifted twice over the compiler's history, but
neither change is a fix and neither reaches the requested message:

| releases | wording |
| --- | --- |
| v1.4.1907 – v1.5.2010 | access violation (crash), no diagnostic text |
| v1.6.2104 | access violation with internal-error text |
| v1.6.2106 – v1.6.2112 | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` |
| v1.7.2207 – v1.9.2607, `main` | `error: llvm::cast<X>() argument of incompatible type!` (current) |

So the earliest checkable releases crash outright, a middle band names the
internal error explicitly, and the current wording drops the "Internal
Compiler error" prefix but is otherwise the same `llvm::cast` message —
still not the "using uninitialized value to access structured buffer"
diagnostic requested here. A control shader with the index initialized
(`uint X = 0;`) compiles cleanly and emits ordinary DXIL, confirming the
failure is specific to the uninitialized read, not the structured-buffer
array-member access in general.

The single existing comment links #5040 for reference; that report is a
different construct (`ByteAddressBuffer.Load` with an uninitialized index)
and a different symptom (silent success with no diagnostic at all, versus
the bad diagnostic reported here), so it's noted but not treated as the
same defect.

Suggest adding **`diagnostic`** — the ask here is specifically about the
quality of the diagnostic text, which is what that label is for. `bug`,
`crash` and `incorrect-code` all still apply as-is.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
