> [!WARNING]
> **Draft -- not a maintainer decision.** AI-assisted triage for
> [#5194](https://github.com/microsoft/DirectXShaderCompiler/issues/5194).

Still reproduces on `main` (Debug build, commit `89e2f98e2`). All three call
forms still error:

```
repro.hlsl:11:5: error: no matching function for call to object of type 'Test'
    t(5);
    ^
repro.hlsl:12:7: error: unexpected type name 'uint': expected expression
    t<uint>(5);
      ^
repro.hlsl:13:7: error: no matching member function for call to 'operator()'
    t.operator()<uint>(5);
    ~~^~~~~~~~~~~~~~~~
```

Compiler Explorer, current `dxc_trunk` alongside CE's oldest DXC
(`dxc_1_6_2112`): https://godbolt.org/z/9ajqv56xK -- identical result on
both.

History: `-HV 2021` didn't exist before v1.6.2112 (2021-12), so older releases
are invalid probes (they reject the flag before parsing anything); `bisect`
reports always-repro'd from v1.6.2112 (17 months before this report) through
the latest release, v1.9.2607. This was never implemented, not a regression.

On the successor Clang-based HLSL front end: testing each call form in
isolation, `hlsl_clang_trunk` already accepts `t(5)` and
`t.operator()<uint>(5)` -- the two forms that are valid C++ -- and only
still rejects `t<uint>(5)`, which isn't valid C++ syntax either. So the
new front end's behavior on this input already matches C++ overload rules.

Suggested labels: no change -- `bug` and `hlsl-next` already describe this
correctly.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
