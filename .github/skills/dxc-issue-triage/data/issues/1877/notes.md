# #1877 DXC ignores struct cast when writing to an AppendStructuredBuffer

**Verdict: still reproduces. Always reproduced (v1.4.1907 - v1.9.2607).**

Ground truth: clean `main` Debug build, 1.9.0.15422 (eff900d5).

## Result

`(I32)f32` should convert a float member to int. Current DXC emits **no `fptosi`**:

```
%3 = call %dx.types.CBufRet.i32 @dx.op.cbufferLoadLegacy.i32(...)
%4 = extractvalue %dx.types.CBufRet.i32 %3, 0
call void @dx.op.bufferStore.i32(..., i32 %4, ...)
```

Note the load is `cbufferLoadLegacy.**i32**` - the float's bit pattern is read as an integer
and stored unconverted. The conversion is not merely lost at the store; the value is never
treated as a float at all.

## Control (the reporter's own)

The issue states it does not repro through `RWStructuredBuffer`. Confirmed:

```
%5 = fptosi float %4 to i32
```

So the predicate discriminates converted from unconverted code, and the defect is specific
to the `Append` path rather than to struct casts generally - exactly as reported.

## FXC comparison (local fxc.exe 10.0.26100)

```
ftoi r0.y, cb0[0].x
store_structured u0.x, r0.x, l(0), r0.y
```

Verbatim the output quoted in the 2019 report.

## History

Always reproduced across v1.4.1907 - v1.9.2607. Both endpoint probes compiled cleanly and
emitted DXIL, so they are valid probes, not silent failures satisfying an absence-based
predicate.

## Assessment

Silent wrong code: no diagnostic, and the module passes validation. A shader reading that
field gets reinterpreted float bits. More dangerous than a crash because nothing surfaces it.
