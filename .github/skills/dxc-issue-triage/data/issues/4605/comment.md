> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4605](https://github.com/microsoft/DirectXShaderCompiler/issues/4605).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on all 20 stable
releases from v1.4.1907 to v1.9.2607:

```
repro.hlsl:4:18: error: Explicit template arguments on intrinsic Load are not supported
  return buf.Load<float4>(idx1);
                 ^
```

`Store<float4>` gets the corresponding `Store` diagnostic. The same templated
operations compile on `RWByteAddressBuffer`, and untemplated `Load` compiles
on `RasterizerOrderedByteAddressBuffer`. Those controls pass on every release,
so none of the 20 predates templated byte-address `Load<T>`/`Store<T>`.

The rejection comes from the explicit-template-argument allow-list in
`tools/clang/lib/Sema/SemaHLSL.cpp:11379`: it names
`ByteAddressBuffer` and `RWByteAddressBuffer`, but not
`RasterizerOrderedByteAddressBuffer`. No current test covers the templated ROV
forms.

[Compiler Explorer](https://godbolt.org/z/nE7zvT4sx) also shows that the
Clang-based front end rejects `Load` on the ROV type with or without template
arguments, so that is a wider implementation gap rather than this exact
defect.

Suggested label: add `up-for-grabs`, matching the maintainer comment that PRs
are welcome although a proactive DXC fix is not planned.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
