> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5338](https://github.com/microsoft/DirectXShaderCompiler/issues/5338).

**Still reproduces on `main`** (`89e2f98e2`; the local build reports
`1.9.0.5465`). A Release build hits your exact quoted text:

```
error: llvm::cast<X>() argument of incompatible type!
```

(confirmed on `dxc_trunk` via Compiler Explorer: https://godbolt.org/z/5nqjfhfve).
A Debug/assertions build instead traps @llvm-beanz's quoted assertion
word-for-word — only the source line moved (2548 → 2630):

```
Error: 	!(onlyUsedByLifetimeMarkers(BCI))
Func:	SROA_Helper::RewriteBitCast
	expected struct bitcast to only be used by lifetime intrinsics
```

Both are the same defect; which one you see just depends on whether asserts
are compiled in.

**FXC does more than avoid the error** — at `/T vs_5_0` it constant-folds the
`[unroll]` loop to `mov o1.xyzw, l(0,1,4,9)` and `mov o2.xyzw, l(16,25,36,49)`
(`n*n` for `n=0..7` across both `SV_ClipDistance` registers). DXC never
handles this input correctly: across all 21 measured releases
(v1.4.1907..v1.9.2607) plus `main`, it either hangs (v1.4.1907, rechecked at
240s), crashes (v1.7.2207 onward), or is diagnosed-rejected by validation in
between (`Not all elements of output SV_ClipDistance were written` in
v1.5.2010..v1.6.2112). That middle window is a different failure mode, not a
fix.

A candidate for the v1.6.2112→v1.7.2207 regression: `#4456` ("Fix memcpy
replacement removing memcpy to output argument") changes exactly how
`LowerMemcpy` treats `out`/`inout` parameter destinations, which is the shape
of `castFunc`'s argument here — but I did not build at that commit to confirm
it, so treat it as a lead, not an attribution.

Current labels (`bug`, `crash`, `fxc-disagrees`) all still fit; no changes
suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
