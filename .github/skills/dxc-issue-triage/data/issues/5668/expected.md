# Expected symptom — #5668

**Reported:** `DispatchMesh` fails when given an empty struct.

Reporter's repro (`a.hlsl`, compiled `dxc a.hlsl -T as_6_6 -E taskMain`):

```hlsl
struct S{};
[shader("amplification")]
[numthreads(1,1,1)]
void taskMain(uint tig_0 : SV_GROUPINDEX)
{
    S s;
    DispatchMesh(1U, 1U, 1U, s);
    return;
}
```

**Reported actual behavior:** DXIL validation fails with

```
error: validation errors
a.hlsl:14:5: error: For amplification shader with entry 'taskMain', payload size 4 is greater than declared size of 0 bytes.
note: at 'call void @dx.op.dispatchMesh.struct.S(i32 173, i32 1, i32 1, i32 1, %struct.S* nonnull %1)' in block '#0' of function 'taskMain'.
Validation failed.
```

reported against `libdxcompiler.so: 1.7(dev;0-00000000)` on NixOS (Linux).

**What "this reproduces" means for this triage:** compiling the identical
source with the identical flags on the Windows `main-debug` ground truth
produces a **DXIL validation failure** whose message states a payload-size
disagreement for the empty-struct payload passed to `DispatchMesh` — i.e. the
front end computes/records a declared payload size of 0 bytes for `struct
S{}` while codegen emits a `dispatchMesh` call whose actual struct size is
non-zero (4, or whatever this build's struct-of-nothing lowering produces),
and the validator (correctly, per the maintainer's 2024-10-10 comment
below) rejects the mismatch.

**Maintainer comment (damyanp, 2024-10-10):** "We think that the validator is
correctly complaining about bad code that the compiler generated, so
removing the validation label." This reframes the bug: it is not a validator
false positive, it is that codegen/front-end size-computation for an empty
struct disagrees with itself. So "this reproduces" specifically means: the
compile still fails validation with a payload-size mismatch message
attributable to the empty struct, not that the validator itself is wrong.

**Repro quality:** `complete` — full self-contained single-file HLSL repro
and exact command line are given in the issue body.

**Not this issue:** an issue where `DispatchMesh` with an empty struct simply
compiles clean and validates (which would mean the front end's declared
payload size for `S{}` now agrees with what codegen emits — either by
codegen no longer inflating the size, or by rejecting `S{}` as a payload
type earlier, with a diagnostic, before ever reaching the validator).
