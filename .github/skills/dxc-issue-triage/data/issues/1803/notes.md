# #1803 [RW]StructuredBuffer<matrix> ignores orientation

**Verdict: still reproduces. Always reproduced (v1.4.1907 - v1.9.2607).**

Ground truth: clean `main` Debug build, 1.9.0.15422 (eff900d5).

## What was tested

`repro.hlsl` is the reporter's shader verbatim, `-T ps_6_0 -E main`.

## Result

```
call void @dx.op.bufferStore.i32(i32 69, %dx.types.Handle %1, i32 0, i32 0,
                                 i32 11, i32 21, i32 12, i32 22, i8 15)
```

`int2x2(11,12,21,22)` sets m[0][0]=11, m[0][1]=12, m[1][0]=21, m[1][1]=22, so a row-major
store must write **11,12,21,22**. DXC writes **11,21,12,22** - column-major.

## The control is what makes this conclusive

Compiling the identical shader with `column_major` substituted for `row_major` produces
**byte-identical DXIL**. The attribute is not mis-applied; it is discarded. This matches the
mechanism the reporter identified: the typedef's attribute is stripped by
`Sema::CheckTemplateTypeArgument` canonicalisation, so the specialisation is really
`RWStructuredBuffer<matrix<int,2,2>>`.

## FXC comparison (run locally, Windows SDK 10.0.26100 fxc.exe)

```
store_structured u0.xyzw, l(0), l(0), l(11,12,21,22)
```

Byte-for-byte the output quoted in the 2018 report. The FXC contrast still holds.

## History

`bisect`: `repro` at both v1.4.1907 and v1.9.2607 - always reproduced across every
checkable release. The bisection floor is v1.4.1907, so "always" means "for as long as it
is possible to check", not "since the issue was filed" (Dec 2018 predates the floor).

## Assessment

Real, current, silent wrong-code with a verified control and a known mechanism. The
reporter also notes FXC rejects `RWStructuredBuffer<row_major int2x2>` outright and ignores
`/Zpr`, so *what* the correct behaviour should be has a language-design component - but
"the attribute is silently dropped" is not defensible under any of the options.
