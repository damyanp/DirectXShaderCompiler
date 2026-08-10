> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4096](https://github.com/microsoft/DirectXShaderCompiler/issues/4096).

Still reproduces on `main` (`13730886e`, `dxc 1.9.0.5433`), and the diagnosis in the thread is
still accurate — but the failure has changed shape, and Clang has since answered the question.

**Current DXC.** `dxc -T cs_6_0 -E main -HV 2021` on the shader from the description:

```
repro.hlsl:3:3: error: conversion operator overloading is not allowed
  operator bool() {
  ^
repro.hlsl:11:7: error: value of type 'Foo' is not contextually convertible to 'bool'
  if (A)
      ^
```

The second error is the reported symptom. The first is new: PR #8206 (`b13e386be`, 2026-04-14)
added `err_hlsl_unsupported_conversion_operator`, so the declaration itself is now rejected.
That is the only commit touching `SemaDeclCXX.cpp` between v1.9.2602.24 and v1.9.2607. The
construct now fails earlier; it does not work.

**History.** Linear sweep of 20 stable releases: the symptom is present in all 16 that can
compile the input, v1.6.2112 (2021-12-08) through v1.9.2607. The four older ones answer
`Unknown HLSL version: 2021` and never ran it — confirmed with a minimal `-HV 2021` shader
that they also reject. v1.6.2112 shipped 16 days after this report, so no stable release
covers the build it was filed against.

The operator body has never run. Making the two candidate conversions disagree — `operator
bool() { return x > 5; }` with `x == 1`, storing 222 if the operator runs and 111 if it does
not — all 15 releases from v1.6.2112 to v1.9.2602.24 emit `i32 111` for `(bool)A`: the
flat conversion, not the operator.

**The 2023-02-08 comment is still correct.** `SemaOverload.cpp` line 1136 at `13730886e` is
`if (SuppressUserConversions || S.getLangOpts().HLSL)` in `TryUserDefinedConversion`, so no
user-defined conversion is ever considered, which is why the diagnostic is the generic "not
contextually convertible".

**Clang already does this.** [Compiler Explorer](https://godbolt.org/z/6Y38q1bn9): both DXC
panes fail, `hlsl_clang_trunk` compiles the shader. With an observable attached to the same
`if (A)`, Clang emits `bufferStore(..., i32 222, ...)` — it invokes `operator bool()` in the
condition. Controls compiling the same shader without the operator, and the buffer store on
its own, both succeed, so the acceptance is about the conversion rather than the stage or the
resource. (For an explicit `(bool)A` cast Clang currently does the same flat conversion the
older DXC releases do; that is a different expression from the one reported here.)

**Suggested labels:** add `type-system` and `enhancement`, keep `hlsl-next`. It has never
worked in any release that can express it, and the enabling change is a language-version
feature rather than a regression.

**The design position may already be on record.** This is milestoned HLSL 202x. In
[`microsoft/hlsl-specs` PR #37](https://github.com/microsoft/hlsl-specs/pull/37#discussion_r1158553249),
llvm-beanz said operator additions may depend on planned 202x overload-resolution work. That
comment concerned built-in operators rather than this conversion specifically, so it may or may
not apply here.

Whether DXC keeps tracking this — now that the declaration is a hard error and the successor
front end implements the behaviour — is a product and language decision, not something this
triage should pre-empt.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
