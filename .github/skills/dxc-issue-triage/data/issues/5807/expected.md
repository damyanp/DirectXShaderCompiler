# Expected symptom (#5807)

Repro quality: **complete** (issue body gives a complete, minimal, compilable shader; author's
own godbolt link is quoted but not treated as authoritative since it is a trunk build, not a
release).

Reported symptom: compiling

```hlsl
enum E : uint {
    A,
    B
};

float4 PSMain() : SV_Target0 {
    uint e = E::A << 1u;
    return 0.0;
}
```

produces a spurious diagnostic:

```
error: cannot convert from 'unsigned int' to 'E'
```

on the left-shift `E::A << 1u`, even though `E` is an **explicitly-typed, non-`class`**
(unscoped) enum, which in C++ implicitly converts to its underlying integer type for this kind
of expression. The reporter says the same code with `|` in place of `<<` compiles fine, and
that FXC/other C++ compilers he tried do not reject an equivalent construct.

Maintainer `llvm-beanz` confirmed in a comment (2023-10-03) that this is caused by
`HLSLExternalSource::CanConvert` in `SemaHLSL.cpp` not correctly handling the implicit
conversion of an explicitly-typed non-class enumeration to its underlying type, and noted the
same defect is expected to go away once HLSL 202x adopts C++ overload-resolution rules
(hence the `hlsl-next` label as well as `bug`).

**"Reproduces" for this issue means:** compiling the exact repro above (`-T ps_6_0 -E PSMain`,
no special `-HV` needed since unscoped enums compile under the default language version) still
emits `error: cannot convert from 'unsigned int' to 'E'` (or an equivalent Sema diagnostic
naming the same conversion) instead of compiling cleanly. "Does not reproduce" means the shader
compiles without error and produces DXIL for `PSMain`.

Because the symptom is a spurious *diagnostic* on valid-looking code, this needs both control
directions (see `match.json` / `variant-*` captures):
- a **positive control** proving the compiler still parses/diagnoses enums and this general
  shape of shader at all (e.g. an out-of-range case or the same enum used with `|`), and
- a **positive anchor** that the diagnostic clause only fires on the exact reported conversion,
  not on any error at all.
