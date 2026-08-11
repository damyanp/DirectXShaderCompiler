> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4648](https://github.com/microsoft/DirectXShaderCompiler/issues/4648).

Still reproduces on `main` (`13730886e`) and on all 20 stable releases from
v1.4.1907 through v1.9.2607. The oldest two exit with `0xC0000005` and empty
stderr; v1.6.2104 onward print:

```text
Internal compiler error: access violation. Attempted to read from address 0x0000000000000008
```

The Debug build first hits the `DeclSpec.cpp:640` and `Type.h:581` null-type
asserts; continuing reaches the same access violation. In
`HLSLExternalSource::ApplyTypeSpecSignToParsedType`,
`return m_scalarTypes[newScalarType];` can return a null lazily-created scalar
type. Naming the corresponding unsigned type earlier primes that slot and makes
the unchanged declaration compile.

The defect is broader than the title: locals, parameters, struct members,
`unsigned int32_t`, `unsigned int64_t`, and
`typedef int MyInt; unsigned MyInt g;` also crash. Vector and matrix spellings
escape because `LookupVectorType`/`LookupMatrixType` perform the scalar lookup
first. The only in-tree coverage is for those working shorthand forms.

[Compiler Explorer](https://godbolt.org/z/ejc1rnGPq) shows DXC trunk and
v1.6.2112 crashing while the primed control compiles; Clang-HLSL rejects the
construct instead.

Suggested label: add **`type-system`**; `bug` and `crash` already fit.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
