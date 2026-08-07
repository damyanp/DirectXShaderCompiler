> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1768](https://github.com/microsoft/DirectXShaderCompiler/issues/1768).

Still reproduces on `main` (1.9.0.15422, `eff900d5`), and in every release from v1.4.1907
through v1.9.2607. It crashes rather than erroring.

Repro: https://godbolt.org/z/b66vK5EPx

```hlsl
struct GSInOutNested { float value : TEXCOORD0; };
struct GSInOut { GSInOutNested nested[1]; };

[maxvertexcount(1)]
void main(point GSInOut input[1], inout PointStream<GSInOut> output)
{
    output.Append(input[0]);
}
```

The failure looks different depending on the build, and on trunk between runs of the same
input — worth recording, because it makes this easy to mis-triage:

| Build | Result |
| --- | --- |
| `main` Debug | assert / internal compiler error (`0x80000003`) |
| v1.4.1907 | access violation (`0xC0000005`) |
| v1.6.2112 (Linux) | `SIGSEGV` |
| trunk (Linux) | `SIGSEGV` on some runs, `error: cast<X>() argument of incompatible type!` on others |

Two separable issues:

1. **Feature gap** — arrays of structs in GS streams are unimplemented. The 2018 comment above
   explains why it is awkward: DXIL has arrays but not structs, so `struct { int; float; }[42]`
   must lower to `int[42]; float[42]`, perturbing layout and semantic ordering.
2. **Failure mode** — that unimplemented case crashes instead of diagnosing.

Even if (1) is never implemented, (2) is worth fixing on its own: reject the construct with a
clear message.

**Labels:** suggest adding `crash` (currently labelled only `bug`, though it access-violates in
shipping builds) and `diagnostic`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
