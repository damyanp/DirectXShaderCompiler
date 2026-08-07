> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#3873](https://github.com/microsoft/DirectXShaderCompiler/issues/3873).

Still reproduces on `main` (1.9.0.15422, `eff900d5`), and in every release from v1.4.1907
through v1.9.2607.

Repro: https://godbolt.org/z/6z6j7Ma36

```hlsl
struct Helper { float getColor() { return 0; } };   // empty
struct Parent { Helper helper; };
struct Child : Parent
{
	float memberVar;
	float color() { return helper.getColor(); }
};

RWStructuredBuffer<float> output;

[numthreads(1, 1, 1)]
void main()
{
	Child instance;
	output[0] = instance.color();
}
```

| Build | Result |
| --- | --- |
| Release (v1.9.2607) | no output; still running after 5 minutes |
| `main` Debug | LLVM assert in ~2 seconds, same input |
| Clang (trunk) | compiles cleanly |

Giving `Helper` a member makes it compile, which confirms the empty struct is the trigger.

The Debug assert and the Release hang may or may not share a cause; flagging only because a
Debug build fails fast here and a Release build does not fail at all, so the two configurations
look like different bugs.

The link restates the original `ps_6_0` as a compute shader so Clang can run the same source;
the original hangs identically.

**Labels:** suggest adding `type-system`. `crash` is the closest existing fit, though in a
shipping Release build this hangs rather than crashing.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
