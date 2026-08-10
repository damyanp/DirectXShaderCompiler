> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4341](https://github.com/microsoft/DirectXShaderCompiler/issues/4341).

Still reproduces: there is no way to write through a user-defined `operator[]` on
`main` (1.9.0.5433, `13730886e`) or on any release that supports HLSL 2021.

The issue supplies the getter but not the failing assignment, profile or command line. The
`m[0] = 9.0` harness below is reconstructed around that quoted struct, so repro quality is
partial.

The assignment is **rejected**, not silently dropped:

```
repro.hlsl:31:8: error: expression is not assignable
  m[0] = 9.0;
  ~~~~ ^
```

The repro seeds `A[0]` with `1.0`, runs `m[0] = 9.0;`, and returns `A[0]`, so a write that
landed and a write that was discarded would give different values. No release produces
either — the compile always fails, so this has been a diagnostic throughout rather than a
silent miscompile.

The two explanations in the thread still hold:

| | on `main` today |
| --- | --- |
| `float4 &operator[](int ix)` — the C++ setter spelling | `error: references are unsupported in HLSL` (`Sema::BuildReferenceType` rejects every reference type in HLSL, `tools/clang/lib/Sema/SemaType.cpp:1921-1925`) |
| a `const` getter beside a non-const setter | `error: class member cannot be redeclared` — the trailing `const` is not part of the signature, so the pair is a redeclaration, not an overload |
| a named `Set(int, float4)` method | works — the store lands, so mutating `A[]` from a member function is not the obstacle |

Reading through the same operator compiles cleanly, which is the control: the rejection is
specific to writing through it, not to `operator[]` or to HLSL 2021 support.

The diagnostic itself is not wrong — assigning to a prvalue is ill-formed in C++ too. What
is missing is a way to spell an overload that returns something assignable, so this is a
language gap rather than a DXC-side bug.

**Release history:** rejected identically on all 16 stable releases from v1.6.2112 (the first
release that accepts `-HV 2021`) through v1.9.2607. `-HV 2021` is required through
v1.7.2212.1 and inert from v1.7.2308, where the default moved. v1.4.1907, v1.5.2010,
v1.6.2104 and v1.6.2106 answer `Unknown HLSL version: 2021` for both the repro and a
feature-presence control, so they predate the language mode and are not evidence either way.

The Clang-based front end rejects this identically today.
[Compiler Explorer](https://godbolt.org/z/Y5d6e1r16) —
`hlsl_clang_trunk -fsyntax-only` emits the identical `expression is not assignable` at the
same column as both DXC panes, and the last pane compiles the same source with the assignment
removed (`-DCONTROL_NO_ASSIGN`) at exit 0, so the Clang result is not an artefact of
incomplete HLSL support.

Labels: this carries no kind label, so it does not show up in a feature-request search —
suggest adding `enhancement` and `hlsl2021` (the construct only exists under `-HV 2021`),
keeping `hlsl-next`. Whether the fix arrives as reference support, as
[const instance methods](https://github.com/microsoft/hlsl-specs/blob/main/proposals/0007-const-instance-methods.md),
or only in the Clang implementation is a language decision, not something this triage settles.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
