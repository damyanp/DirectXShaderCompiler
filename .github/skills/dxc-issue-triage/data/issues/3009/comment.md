> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3009](https://github.com/microsoft/DirectXShaderCompiler/issues/3009).

Still reproduces on `main` (1.9.0.15422, `eff900d5`), and in every release from v1.4.1907
through v1.9.2607.

Repro: https://godbolt.org/z/5bdo83bTY

```hlsl
int2x2 m;
RWStructuredBuffer<int2> output;

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
	int2 b;
	b.x = tid.x;      // b.y is never assigned
	output[0] = mul(b, m);
}
```

The uninitialized half reaches arithmetic:

```llvm
%11 = call i32 @dx.op.tertiary.i32(i32 48, i32 undef, i32 %6, i32 %10)  ; IMad(a,b,c)
```

Same source, three compilers:

| Compiler | Result |
| --- | --- |
| FXC | `error X4000: variable 'b' used without having been completely initialized` |
| DXC | exits 0, no diagnostic, `i32 undef` into `IMad` |
| Clang (trunk) | identical `undef`, also no diagnostic |

One trap worth knowing if anyone tests for this: `undef` alone is not a usable signal. Some
DXIL ops carry structurally-undef operands in correct code — `loadInput`'s trailing
`gsVertexAxis` and `bufferStore`'s unused coordinates both appear as `undef` in the output
above.

The link restates the original `vs_6_2` repro as a compute shader so all three compilers can
run the same source; the original behaves the same way, as does @pow2clk's `SV_Position`
variant.

**Labels:** `validation` looks correctly applied, given the note above that the validator
should be able to detect this. Suggest adding `diagnostic` and `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
