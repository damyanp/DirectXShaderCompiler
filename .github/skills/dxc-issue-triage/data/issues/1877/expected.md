# Expected symptom - #1877 DXC ignores struct cast when writing to an AppendStructuredBuffer

**Repro quality: complete.** Full source and the relevant DXIL excerpt are given.

## What was reported (2019-01-23)

```hlsl
struct I32 { int value; };
struct F32 { float value; } f32;
AppendStructuredBuffer<I32> output;
void main() { output.Append((I32)f32); }
```

The struct cast `(I32)f32` should convert the `float` member to `int`. DXC emits the cbuffer
load and stores it straight into the buffer with **no `fptosi`** - the raw float bit pattern is
written into an `int` field. FXC emits `ftoi`.

## The symptom reproduces if

The generated DXIL contains **no `fptosi`** between the cbuffer load and the `bufferStore`, i.e.
the float value reaches the store unconverted.

## Control (supplied by the reporter)

"It does not repro using an `RWStructuredBuffer`." So the same cast through
`RWStructuredBuffer<I32>` must **contain** `fptosi`. That control does two jobs: it proves the
predicate can distinguish converted from unconverted code, and it confirms the defect is
specific to the `Append` path rather than to struct casts generally.

## Note

Reading the raw bits of a float as an int is silent wrong-code: no diagnostic, and the shader
validates. That makes it materially worse than a crash.
