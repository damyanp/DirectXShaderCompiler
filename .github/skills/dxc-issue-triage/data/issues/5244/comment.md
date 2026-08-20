> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5244](https://github.com/microsoft/DirectXShaderCompiler/issues/5244).

**Still reproduces** on `main` (upstream `89e2f98e29c2`, Debug build; the local binary
self-reports a fork-local merge commit whose source tree is identical to that public commit
outside triage tooling). With the repro exactly as filed:

```
$ dxc -spirv -Zi -fspv-reflect -E PS -T ps_6_7 repro.hlsl
Internal compiler error: LLVM Assert            # exit 0xE0000001
```

The same shader compiles cleanly to DXIL, matching what the original report showed.

Two things worth adding to the original report:

**It's a crash, not only an unimplemented case.** Under a debugger, this trips two chained
asserts in `clang::spirv::PreciseVisitor::isAccessingPrecise`
(`tools/clang/lib/SPIRV/PreciseVisitor.cpp:72`, then `include/llvm/ADT/ArrayRef.h:197`) — an
out-of-range access into the multisample resource's SPIR-V struct fields. Continuing past both
(emulating a Release/`NDEBUG` build) shows the *codegen itself* is broken, not just the assert:
DXC's own embedded SPIR-V validator then rejects the module it just built:

```
fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-UniformConstant-04655]
UniformConstant OpVariable <id> '7[%gUav]' has illegal type.
```

**Every shipped release fails the same way, just without the debugger.** All 19 probeable
stable releases from v1.5.2010 (2020-10, before this issue was filed) through v1.9.2607 hit
the same invalid-SPIR-V path; with the assert compiled out under `NDEBUG` they get far enough
for the validator to reject it cleanly instead (exit `E_FAIL`, older releases print a
plainer `error: unknown shader module: invalid`). v1.4.1907 was not built with SPIR-V
support at all and can't probe this. So this has never worked in SPIR-V, on any checkable
release — not a regression, and not close to fixed on `main` either.

[Compiler Explorer](https://godbolt.org/z/oj91s731v): `dxc_1_6_2112` and `dxc_trunk` both
still fail the same way.

Suggested labels: add **`bug`** and **`crash`** alongside the existing `enhancement` — this
is more than a missing feature, it's a reachable assert from valid HLSL.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
