> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5674](https://github.com/microsoft/DirectXShaderCompiler/issues/5674).

Still reproduces on `main` (89e2f98e2, Debug build):

```
Internal compiler error: access violation. Attempted to read from address 0x0000000000000038
```

Compiler Explorer: https://godbolt.org/z/bsEPd3eaY — `dxc_1_6_2112` (oldest available there)
rejects the declaration cleanly; `dxc_trunk` crashes (`SIGSEGV` on Linux, same defect as the
Windows access violation).

**History:** bisected across the 20 stable releases back to v1.4.1907 (2019-07). This did
*not* always crash. Through v1.6.2112 (2021-12-08), `float2x2 matrix;` was rejected outright
at parse time:

```
error: template specialization requires 'template<>'
error: cannot refer to class template 'matrix' without a template argument list
```

Starting at v1.7.2207 (2022-07-18) that declaration is accepted, and using `matrix` afterward
crashes instead. The transition lines up with `a7fa058dd` ("Rework name lookup", #4332,
2022-04-12), whose own description says it made bare `matrix` (no `<>`) valid in HLSL — that
appears to have also made it possible to shadow `matrix` as a variable name, which the
overload-resolution path for `*` doesn't handle: the crash is in `ArgumentDependentLookup` /
`FindAssociatedClassesAndNamespaces`, dereferencing an invalid `ValueDecl` for the `matrix`
operand. This attribution is strong but not proven (the exact commit wasn't built and tested
in isolation).

Suggest adding `matrix-bug` alongside the existing `bug`/`crash`/`incorrect-code` labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
