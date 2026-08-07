> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3048](https://github.com/microsoft/DirectXShaderCompiler/issues/3048).

Still reproduces on `main` (1.9.0.15422, `eff900d5`), and in every release from v1.4.1907
through v1.9.2607.

Repro: https://godbolt.org/z/1o5Exs9YP

```hlsl
struct A { float4 stuff; };
struct B : A { float4 gimme() { return stuff; } };
struct C : B { void dostuff() { stuff = 0; } };

float4 f(B thing1) { return thing1.gimme(); }   // passing a C here is the trigger

RWStructuredBuffer<float4> output;

[numthreads(1, 1, 1)]
void main()
{
	C thing2;
	thing2.stuff = float4(1, 2, 3, 4);
	output[0] = f(thing2);
}
```

| Compiler | Result |
| --- | --- |
| DXC `main` Debug | LLVM assert in codegen |
| DXC v1.6.2112 and trunk (Linux builds) | `SIGSEGV` |
| Clang (trunk) | compiles cleanly |

Changing `f`'s parameter from `B` to `C` compiles, which isolates the derived-to-base
conversion rather than the inheritance itself.

The link restates the original `ps_6_0` as a compute shader so Clang can run the same source;
the original crashes identically.

**Labels:** Clang compiles this cleanly, so `check-in-clang` may have been answered — removing
it is a maintainer call. Suggest adding `type-system`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
