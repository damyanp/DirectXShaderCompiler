> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3444](https://github.com/microsoft/DirectXShaderCompiler/issues/3444).

Still reproduces on `main` (1.9.0.15422, `eff900d5`). Checked against all 20 releases from
v1.4.1907 to v1.9.2607: every one fails on this input, so despite #3043 and the later revert,
no shipped release has ever produced a proper diagnostic for it.

Repro: https://godbolt.org/z/d6jG8Yjrr

```hlsl
RWStructuredBuffer<float4> rwTexture;

[numthreads(1, 1, 1)]
void CSMain(float id : SV_DispatchThreadID)   // float, not uint
{
	rwTexture[3] = id.xxxx;
}
```

`float2`, `float3` and `float4` fail identically to `float`, so the vector forms noted in the
title are affected too. `uint3` compiles cleanly, isolating the non-integral type.

| Compiler | Result |
| --- | --- |
| FXC | `error X4555: invalid type used for 'SV_DispatchThreadID' input semantics, must be integral` |
| Clang (trunk) | `error: attribute 'SV_DispatchThreadID' only applies to a field or parameter of type 'uint/uint2/uint3'` |
| DXC | `error: cast<X>() argument of incompatible type!` |

DXC does reject the shader, but the message is a leaked internal LLVM assertion rather than an
HLSL diagnostic. FXC and Clang both name the semantic and the expected type.

The severity has softened over the years without the defect being fixed, which is worth knowing
when reading older reports: v1.4.1907–v1.6.2104 access-violated silently (`0xC0000005`), and
from v1.6.2106 onward it is caught and reported as the `cast<X>()` message above.

**Labels:** `diagnostic` and `tech-debt` both look right. Suggest adding `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
