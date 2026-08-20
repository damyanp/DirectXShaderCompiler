# Expected symptom — #5563

Filed against DXC 1.7.0.3939 (5e080a772), compiling for **SPIR-V** with
`-spirv -HV 2021`.

The repro is a partial template specialization:

```hlsl
template <bool PARAM1, bool PARAM2>
struct TEST_STRUCT{};

template <bool PARAM1>
struct TEST_STRUCT<PARAM1, true> {
   static const bool FIELD = PARAM1;
};

struct PSInput
{
    float4 color : COLOR;
};

float4 PSMain(PSInput input) : SV_TARGET
{
    bool test = TEST_STRUCT<true, true>::FIELD;
    return input.color;
}
```

**Reported behavior:** compilation fails with

```
fatal error: found unregistered decl
note: please file a bug report on ... with source code if possible
```

pointing at the partially-specialized template's `PARAM1` parameter
declaration (`template <bool PARAM1>` on line 7 of the snippet, i.e. the
`TEST_STRUCT<PARAM1, true>` partial specialization).

**"Reproduces" means:** compiling the shader above with
`-T ps_6_0 -E PSMain -spirv -HV 2021` emits the `found unregistered decl`
fatal error from `DeclResultIdMapper::getOrRegisterFn`/`getDeclResultId`
(`tools/clang/lib/SPIRV/DeclResultIdMapper.cpp`), i.e. the SPIR-V backend
never registered a `mapping::MemberVariableInfo`/result-id for the static
`const bool FIELD` member of the partial specialization before code
generation tried to read it.

**"Does not reproduce" means:** the same command compiles successfully (exit
0) and emits valid SPIR-V for `PSMain`, with `test` folded to the value of
`PARAM1` (`true` for the filed invocation) or otherwise correctly
initialized.

This is a compile-time diagnostic issue, not a runtime/GPU one — a Debug
`dxc.exe` invocation is sufficient to observe it; no GPU execution or driver
is needed. `emitFatalError` (`DeclResultIdMapper.cpp:1048`) is the SPIR-V code
generator's own defensive diagnostic (a `DiagnosticsEngine::Fatal`-level
`clang::Diag`), not an assert or a crash — it is expected to end the compile
with an ordinary diagnosed-error exit status, not to trip a debugger-visible
assert. `internal_failure` as defined by this skill (exit codes
0xC0000005, 0x80AA0018, 0x80000003, 0xE0000001-3, etc.) is not the expected
signature here; the predicate should match on the literal diagnostic text
instead, anchored so it cannot be satisfied by an unrelated compile failure.

Repro quality: **complete** — the issue body contains the full shader, the
exact command-line flags, and the exact diagnostic text.
