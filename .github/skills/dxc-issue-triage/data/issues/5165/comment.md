> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5165](https://github.com/microsoft/DirectXShaderCompiler/issues/5165).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), and always has:
a linear scan of every stable release from v1.4.1907 through v1.9.2607 reproduces it, so this
has never worked, not regressed.

@damyanp is right that this isn't a validation bug: the validator is correctly rejecting IR
that should never have been generated. The root cause is in `SimplifyCFG`'s
`SwitchToLookupTable` transform. When a switch's optimizer-generated lookup table has "holes"
and the `default:` case can't be folded to a compile-time constant, the transform builds a
"hole check" bitmask whose width is `NextPowerOf2(max(7, TableSize - 1))`. For a table size of
8 or less that's exactly 8, producing an illegal `i8` truncation:

```
error: I8 can only be used as immediate value for intrinsic or as i8* via bitcast by lifetime
intrinsics.
note: at '%10 = trunc i32 %3 to i8' in block '#2' of function 'ShaderDomain_Cs'.
```

This is the sibling of a bug already fixed for the switch's separate *result* bitmap (rounded
up to >= 16 bits in a prior fix for a different, unrelated issue) — but that fix never touched
this "hole check" mask width computation, which still uses the old formula.

Minimal repro (reconstructed; the original Shader Playground link is dead):

```hlsl
RWStructuredBuffer<uint> buf : register(u0);

[numthreads(1,1,1)]
void ShaderDomain_Cs(uint3 id : SV_DispatchThreadID)
{
    uint x = buf[0];
    bool result;
    switch (x)
    {
    case 0: result = true; break;
    case 1: result = true; break;
    case 2: result = true; break;
    case 3: result = true; break;
    case 4: result = true; break;
    case 5: result = true; break;
    case 7: result = true; break;
    default: result = (buf[1] != 0);
    }
    buf[0] = result ? 1 : 0;
}
```

Compiler Explorer (dxc 1.6.2112 and trunk both fail the same way):
https://godbolt.org/z/qPfqjxxnY

Suggested label: `correctness`, in addition to `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
