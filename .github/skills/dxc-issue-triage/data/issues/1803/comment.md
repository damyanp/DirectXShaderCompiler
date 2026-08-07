> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1803](https://github.com/microsoft/DirectXShaderCompiler/issues/1803).

**Still reproduces** on `main` (1.9.0.15422, eff900d5), and on every release from v1.4.1907
to v1.9.2607.

Substituting `column_major` for `row_major` produces **byte-identical DXIL**:

```
call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 0, i32 0,
                                 i32 11, i32 21, i32 12, i32 22, i8 15)
```

`int2x2(11,12,21,22)` gives m[0][0]=11, m[0][1]=12, m[1][0]=21, m[1][1]=22; honouring
`row_major` would store 11,12,21,22. FXC (SDK 10.0.26100) emits
`store_structured u0.xyzw, l(0), l(0), l(11,12,21,22)`, matching the original report.

Repro with an FXC pane: https://godbolt.org/z/4K5T5G5Wf

This is consistent with your diagnosis that template-argument canonicalisation strips the
typedef attribute, yielding `RWStructuredBuffer<matrix<int,2,2>>`.

FXC rejects `RWStructuredBuffer<row_major int2x2>` and ignores `/Zpr` here, so the intended
behaviour still needs a design decision.

Suggested labels: `correctness`, `fxc-disagrees`, `type-system`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag anything that looks wrong.</sub>
