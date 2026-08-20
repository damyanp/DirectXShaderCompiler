# Issue #5338 -- Arrays cast compiler error

## Reported symptom

Reporter (`gauss11`, 2023-06-28): compiling the attached `test.hlsl` with
`dxc -T vs_6_0 test.hlsl` produces

```
// Internal Compiler error: llvm::cast<X>() argument of incompatible type!
```

Reporter states HLSL compilers 5.1 and earlier (i.e. legacy FXC) compile the
same source without a type-cast error.

The shader casts an `out` array parameter to a differently-sized array type
inside a loop:

```hlsl
void castFunc(out float4 afClipD[MAX_CLIPPINGPLANES_CASCADE_>>2])
{
    [unroll]
    for (int n=0;n<MAX_CLIPPINGPLANES_CASCADE_;++n)
        ((float[MAX_CLIPPINGPLANES_CASCADE_])afClipD)[n]=float(n*n);
}
```

## Maintainer comment (2023-06-30, `llvm-beanz`, COLLABORATOR)

> The bug is caused by SROA and related passes making unsafe assumptions
> about bitcasting, which is a gnarly problem and we'll have to look into.
> With asserts enabled the following error message is produced:
>
> ```
> expected struct bitcast to only be used by lifetime intrinsics
> Assertion failed: (false && "expected struct bitcast to only be used by
> lifetime intrinsics"), function RewriteBitCast, file
> ScalarReplAggregatesHLSL.cpp, line 2548.
> ```

So the symptom has two build-dependent faces of the *same* defect, exactly
the shape SKILL.md step 4 calls out: a Release build (asserts compiled out)
takes the reporter's `llvm::cast<X>() argument of incompatible type!` E_FAIL
path; a Debug/assertions build (our ground truth) instead traps the
`RewriteBitCast` assertion in `ScalarReplAggregatesHLSL.cpp`. Both are the
compiler failing internally on a legally-typed-but-unusual array cast that
FXC accepted. `internal_failure` (signature-independent: exit-code based,
see SKILL.md step 4) is the correct predicate family; it does not depend on
either message's exact text.

## What "this reproduces" means

`dxc -T vs_6_0 repro.hlsl` (entry point defaults to `main`, matching the
issue) exits with an internal-failure status (assert trap 0x80000003 or
0xE0000001 on a Debug/assertions build; E_FAIL 0x80004005 carrying an
`llvm::cast<...>` / `cast<...>` marker, or an access violation, on a Release
build) instead of a clean compile or an ordinary diagnosed error.

## What "fixed" means

`dxc -T vs_6_0 repro.hlsl` exits 0 and produces DXIL (or exits with an
*ordinary* diagnosed HLSL error unrelated to the bitcast/SROA machinery,
e.g. a real type-checking rejection of the construct) -- not a crash and not
an internal-error status.

## Repro quality

`complete` -- the issue body supplies the exact command line and the full
source file verbatim; no reconstruction was needed.

## Cross-reference note

The issue's timeline shows one cross-reference, `#5987` ("Error assigning
struct into amplification payload"), created 2023-11-08, predating this
triage. Both concern the SROA/bitcast machinery but describe different
surface symptoms; a duplicate/relatedness judgement is left to batch
collation, not asserted here.
