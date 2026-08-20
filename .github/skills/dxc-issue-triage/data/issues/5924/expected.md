# Expected symptom (#5924)

Title: "Cannot do swizzle operations with floating type when it's a typename"

Reporter's repro is a class template `StyleClipper<float_t>` whose static method
`func(float_t t)` calls `t.xx` (a swizzle) on a parameter whose *declared* type is the
template type parameter `float_t` itself (not a concrete scalar type spelled in the
template body). When `StyleClipper<float>::func` is instantiated, `t`'s real type is
`float`, so `t.xx` should be a completely ordinary `float2` swizzle -- but the reporter
says this fails to compile, while replacing the parameter's static type with the
literal spelling `float` (removing the template dependency entirely) compiles fine.

So "reproduces" means: compiling the reporter's repro (`-T ps_6_0 -E PSMain`, unchanged)
produces a **diagnostic/compile failure** referring to `.xx` / member access on `t`
(e.g. "no member named 'xx'" or similar), where the only structural difference from a
working case is that `t`'s declared type is a dependent template parameter rather than a
literal scalar type name.

"Does not reproduce" means: the exact repro compiles successfully to DXIL with no
errors about `.xx`.

A companion comment from @damyanp says this "looks like it works in clang" (with a
godbolt link), so a Clang comparison pane is directly relevant to this issue
(the `check-in-clang` label already asks for exactly that).

Repro quality: **complete** -- full HLSL source and exact command line given in the
issue body, plus a public godbolt link (not independently fetchable here, but the
inlined source is self-contained and precise).
