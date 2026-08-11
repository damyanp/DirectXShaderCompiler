> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4520](https://github.com/microsoft/DirectXShaderCompiler/issues/4520).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and on all 18 stable
releases with SM 6.6 dynamic resources, v1.6.2104 through v1.9.2607.
v1.4.1907 and v1.5.2010 reject `ps_6_6`, so they are not evidence.

```
repro.hlsl:4:31: error: no matching member function for call to 'Sample'
    float4 result = myTexture.Sample(SamplerDescriptorHeap[sampIdx], coord);
                    ~~~~~~~~~~^~~~~~
repro.hlsl:4:31: note: candidate function template not viable: requires 3 arguments, but 2 were provided
```

All eight tested sampler-taking methods reject an inline heap subscript and
compile when it is hoisted into a local: `Sample`, `SampleLevel`,
`SampleBias`, `SampleGrad`, `SampleCmp`, `SampleCmpLevelZero`, `GatherRed`
and `CalculateLevelOfDetail`. The comparison-state cases used
`SamplerComparisonState`, so this is not a sampler-kind mix-up.

The conversion exists: initialization, an explicit cast and a user-defined
`SamplerState` parameter all compile on every feature-capable build.
`CanConvert` has the heap-to-object case (`SemaHLSL.cpp:10353`), while
intrinsic argument matching reaches `CombineObjectTypes`
(`SemaHLSL.cpp:7354`), which has no heap-sampler case. The intended candidate
is dropped, leaving the generic overload error and arity notes.

The issue body's quoted specification sample is now stale:
[DirectX-Specs#191](https://github.com/microsoft/DirectX-Specs/pull/191)
removed it in 2024. The compiler behaviour did not change. The Clang-based
front end still cannot test this case because it rejects
`ResourceDescriptorHeap` and the workaround as undeclared.

Compiler Explorer: <https://godbolt.org/z/dvYe69hdx>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
