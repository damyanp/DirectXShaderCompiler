> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5668](https://github.com/microsoft/DirectXShaderCompiler/issues/5668).

Still reproduces on `main` (public commit
[`89e2f98e2`](https://github.com/microsoft/DirectXShaderCompiler/commit/89e2f98e29c289ae8ad9e00dd310104fea9fd7df)),
with the identical diagnostic as reported:

```
repro.hlsl:7:5: error: For amplification shader with entry 'taskMain', payload size 4 is greater than declared size of 0 bytes.
```

Confirmed on the current stable release and Compiler Explorer trunk:
https://godbolt.org/z/rqTqed5s8

Bisecting all stable releases back to the oldest one that supports `as_6_6`
(v1.6.2104, 2021-04-20) shows this has never worked; it is not a regression.

**Root cause, from source:** `ValidateAsIntrinsics` in
`lib/DxilValidation/DxilValidation.cpp` measures the payload *pointer's*
`DataLayout` alloc size (a constant 4 bytes, from DXIL's 32-bit pointer
layout) instead of dereferencing to the pointee struct's size, then compares
that constant against the correctly-computed declared size. The declared
size for `struct S{}` is genuinely 0 — `-Vd` still emits a `0`-byte
payload-size record in DXIL metadata — so the check is really testing "declared size < 4", not
"declared size < actual size". That is invisible for every ordinary payload
(real size ≥ 4 bytes), and only fires for a zero-byte one.

So this is a validator bug independent of whether an empty/absent
amplification-shader payload should be legal HLSL (a language-policy
question this doesn't resolve): the validator's own bookkeeping disagrees with itself about the
size of the same value.

This looks like the same defect as #5269 (filed three months earlier),
which independently reaches the same source-level conclusion.

Suggested label: `validation` (in addition to `bug`) — the defect is
entirely inside the DXIL validator's own size comparison, not in front-end
acceptance or in code generation for the payload itself.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the
repro; please flag anything that looks wrong.</sub>
