# Expected symptom — #5039

**Title:** Nonsensical error message when using undef offset in structured buffer

## Reported repro

```
// dxc /Tps_6_0 .\rawbuf.hlsl
struct S {float A[3];};
RWStructuredBuffer<S> buf;

[RootSignature("UAV(u0)")]
float main() : SV_Target
{
    uint X;
    return buf[0].A[X];
}
```

`X` is read without ever being initialized and used as the index into the
fixed-size array member `A` of the structured-buffer element type. The
reporter says compiling this gives:

```
error: llvm::cast<X>() argument of incompatible type!
```

and asks that it instead say something like `error: using uninitialized
value to access structured buffer`.

## What "this reproduces" means

This is **not** a request to make the shader compile silently, and it is
**not** primarily a crash report in the sense of "make it not fail" — the
reporter wants the compile to keep failing, just with a *comprehensible*
diagnostic instead of an internal-looking one. So the symptom under test has
two parts, and both must be scored:

1. **Presence (the reported defect):** dxc's output for this exact shader
   contains the internal-error text `llvm::cast<X>() argument of
   incompatible type!` (or an equivalent `llvm::cast<X>()` internal-failure
   marker). Per the skill's exit-code table, a bad `llvm::cast` throws
   `hlsl::Exception(DXC_E_LLVM_CAST_ERROR, ...)`, which the driver reports as
   plain **E_FAIL (0x80004005)** — the same status as an ordinary diagnosed
   error — so this is scored by matching the internal-failure text marker,
   not by exit status alone. "Reproduces" = this text is still present.
2. **Absence (what a fix looks like):** either (a) the shader now compiles
   successfully (exit 0), because DXIL codegen decided an uninitialized
   array index is not actually a hard error, or, more likely given the
   report, (b) the shader still fails to compile, but with a comprehensible
   diagnostic (e.g. something naming "uninitialized" or the structured
   buffer / array access) and *without* the `llvm::cast<X>()` internal-error
   text. Either (a) or (b) counts as "fixed" for the reported symptom, since
   the ask is specifically about the message, not about making the shader
   legal.

`match.json` therefore anchors on the presence of the `llvm::cast<X>()`
internal-error marker (an `internal_failure` predicate per the skill's
mandatory rule "use `internal_failure` for anything crash-shaped" — this
text marker is the one case the exit code itself cannot distinguish from an
ordinary diagnosed error). No exit-code-only clause is used, because E_FAIL
is shared with a large class of unrelated, correctly-diagnosed errors.

## Repro quality

`complete` — the issue body supplies the exact command line and shader
source, and both match a self-contained `repro.hlsl` / `cmd.txt` pair with no
reconstruction needed.

## Related but distinct

The single comment on the issue says "Related: #5040". #5040 is a different
report (an uninitialized index into `ByteAddressBuffer.Load` silently
compiles with `undef` baked into the DXIL, with *no* diagnostic at all,
contrasted against FXC's `X4575`). It shares the theme of "an uninitialized
index reaching a resource access" but is a different construct (raw buffer
load vs. structured-buffer array-member subscript) and a different symptom
(silence vs. a bad diagnostic), so it is treated here only as background,
not folded into this issue's verdict.
