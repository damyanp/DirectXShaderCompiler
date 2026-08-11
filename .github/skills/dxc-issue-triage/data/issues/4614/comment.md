> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4614](https://github.com/microsoft/DirectXShaderCompiler/issues/4614).

Still reproduces on `main` (1.9.0.5433, `13730886e`), but the title's
“regression” does not match the release history of the attached repro: all 20
stable releases from v1.4.1907 to v1.9.2607 fail.

The assert-enabled build stops in `SROA_Helper::RewriteBitCast`:

```
Error: assert(0 && "Type mismatch.")
File:
lib\Transforms\Scalar\ScalarReplAggregatesHLSL.cpp(2690)
```

Release builds hang instead. Continuing past the assert reaches DXC's own
progress check:

```
Infinite loop while SROA'ing value, use isn't getting eliminated.
```

The source connects the two signatures. The assert is followed by `return`, so
with `NDEBUG` the bitcast use remains; the loop in `RewriteForScalarRepl`
re-selects it, while its `DXASSERT_LOCALVAR` guard is compiled out. A
v1.9.2607 run remained active for 300 seconds, and stack samples 60 seconds
apart stayed at the same depth in the same function.

v1.6.2106, the first release containing `527d58e5a` (“Fixes #3016”), also
hangs. That change and its regression test cover an empty first member, not
the base-class plus empty-member assignment in this repro. The added test
still compiles; this shader does not. Variants that make the base non-empty,
remove the assignment, or replace inheritance with composition compile.

Compiler Explorer: <https://godbolt.org/z/erb45rxTb>. This history applies to
the attached repro; it cannot determine whether the reporter met a new
occurrence in a different production shader.

Suggested labels: add `type-system` and `test`; keep `crash`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
