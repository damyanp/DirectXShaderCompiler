# Expected symptom (written before running anything)

Issue: #5194 "Impossible to add template on operator() overload"

Reported by @kpentaris, 2023-05-09. Repro is a struct with a templated
`operator()`:

```hlsl
struct Test {
    template<typename T>
    T operator()(const T x) {
        return x;
    }
};

[numthreads(32,1,1)]
void main() {
    Test t;
    t(5);                  // error
    t<uint>(5);             // error
    t.operator()<uint>(5);  // error
}
```

The reporter's own Compiler Explorer link (read back via
`GET /api/shortlinkinfo/vx15Ybd1f`) pins the exact configuration: compiler
`dxc_1_7_2207`, options `-spirv -HV 2021 -T cs_6_2`. That is the configuration
`cmd.txt` reproduces; `-E main` is added because CE's default entry point for
this compiler is `main`, matching the shader.

**Reproduces** means: dxc emits a diagnosed compile error (not an internal
failure -- this is not a crash issue) on this source under `-spirv -HV 2021
-T cs_6_2 -E main`, for at least one of the three call forms
(`t(5)`, `t<uint>(5)`, `t.operator()<uint>(5)`). The reporter says "all
syntax tests fail" -- all three lines error in the reported build.

**Does not reproduce** would mean the file now compiles cleanly (exit 0,
valid DXIL/SPIR-V emitted), i.e. DXC's overload resolution now accepts at
least the C++-legal forms.

Maintainer @llvm-beanz (2023-06-30) confirmed this is a known limitation of
DXC's (non-conformant) overload resolution, tied to the "HLSL 202x" adoption
of full C++ overload rules
(https://github.com/microsoft/hlsl-specs/blob/main/proposals/0007-const-instance-methods.md),
not a regression -- i.e. the expectation going in is `always-repro'd`
(never implemented), not a fix/regression pair. A second comment
(2023-08-31, @devshgraphicsprogramming) asks an unrelated question about
`operator=` overloading and is not part of the reported symptom.

Repro quality: **complete** -- the issue body contains the exact failing
source, and CE's stored session pins the exact command line used.
