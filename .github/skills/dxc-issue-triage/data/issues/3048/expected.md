# Expected symptom — #3048 "Casting subclass to parent of three class heirarchy causes crashes"

**Reported (2020-07-22):** with a three-level hierarchy `A <- B <- C`, passing a `C` to a
function taking `B` by value crashes DXC in codegen. Two levels (`B <- C`) is fine, and
passing as `C` is fine.

**Repro quality:** `complete` — a full shader is supplied, plus a maintainer variant.

**What we test:** compile the supplied shader. `repro.hlsl` is the issue's shader verbatim.

**Symptom is present if:** DXC fails internally (assert, access violation, `cast<X>()`
failure) rather than compiling or emitting a clean diagnostic.

**Symptom is absent if:** it compiles, or DXC reports a proper diagnostic.

**Known root cause, which makes this unusually actionable.** @llvm-beanz identified it in
2024-07: the crash is in `CGMSHLSLRuntime::ConvertAndStoreElements` (CGHLSLMS.cpp), reached
via `EmitHLSLFlatConversionAggregateCopy`. He attributes it to PR #2312, which treats
derived-to-base as a *flat* conversion, and notes the AST correctly records it as a
derived-to-base conversion — so codegen is taking the wrong path. His words: "That could
cause all sorts of things to break."

**Therefore also check the blast radius.** If the mechanism is "derived-to-base is miscompiled
as a flat conversion", the interesting question is not only whether the crash reproduces but
whether *non-crashing* derived-to-base conversions produce correct code. A silent wrong-code
case would be more serious than the crash.

**Note:** @llvm-beanz established that derived-to-base is disallowed for `out`/`inout`
parameters, so the by-value case is the only one in scope.

**Profile:** the 2024 stack trace shows `vs_6_0`, but the shader's entry is `float4 main() :
SV_Target`, which is a pixel entry. Try `ps_6_0` first and record which profiles reproduce —
if the crash is profile-independent, that is worth stating.
