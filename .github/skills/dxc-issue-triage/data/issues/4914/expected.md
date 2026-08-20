# Expected symptom — #4914 "[feature request] Copying \"this\" fails"

## What the issue says

Reporter (zeroprey): a member function that **returns or copies `this`** (as opposed to
reading a single member through `this.member`, which already works) fails to compile in DXC,
while FXC accepts the equivalent HLSL. The reporter quotes the exact diagnostic:

```
error: cannot compile this aggregate expression yet
```

and links a shader-playground repro (`https://shader-playground.timjones.io/a60a95d27b98a13ad73f3a8ddeda7a02`,
a third-party host, not used directly here — a local `dxc`-only repro is built instead per the
skill's Compiler Explorer/third-party policy).

Maintainer comment (Keenuts, COLLABORATOR): confirms `this.member` is already supported and
useful for disambiguation, is unsure whether "returning/copying `this`" should be considered a
bug or a language design question ("this would be a pointer [in C++], which in the shader-world
is kinda problematic"), but reports that **compiling the same construct to SPIR-V works** and
looks like it generates valid code — i.e. the DXIL backend is where the failure lives, not the
front end/Sema, and not (necessarily) the SPIR-V backend. That is an unverified secondhand claim
in the thread; this triage re-measures it directly rather than taking it on faith.

Title history is informative: the issue was opened as "Copying \"this\"", renamed to "Copying
\"this\" fails" five days later, then explicitly retitled by a maintainer on 2024-08-22 to
"[feature request] Copying \"this\" fails", with `enhancement` added and the issue milestoned
`Dormant` on the same day. So the maintainers have already classified this as a
feature/design question rather than a plain regression-style bug, even though the reporter's
literal quoted symptom is a hard compile error, not a missing feature per se.

## What "reproduces" means here

The primary, falsifiable symptom is: **compiling a `dxc`-only (DXIL) shader that returns or
copies `this` (a struct-typed `this`, used as a whole aggregate rather than through
`this.member`) fails with the internal-sounding diagnostic**

```
error: cannot compile this aggregate expression yet
```

(the generic Clang CodeGen fallback `ErrorUnsupported(S, "aggregate expression")` in
`tools/clang/lib/CodeGen/CGExprAgg.cpp`'s `AggExprEmitter::VisitStmt`, format string
`"cannot compile this %0 yet"` in `CodeGenModule.cpp`).

This is a **diagnostic-quality/completeness symptom, not a crash**: it is an ordinary
E_FAIL-shaped Clang error emitted through the diagnostics engine, not an assert or an access
violation, so `internal_failure` is not the right predicate kind — a `contains`/`regex` match
on the literal diagnostic text is.

Repro quality: **agent-constructed**. The issue's own shader-playground link is a third-party
host and not reproduced verbatim; a local `.hlsl` exercising the same construct (a member
function returning `this` by value) is built instead, informed by reading
`tools/clang/lib/CodeGen/CGExprAgg.cpp` (no `VisitCXXThisExpr` override on the aggregate
emitter, unlike the scalar emitter `CGExprScalar.cpp:VisitCXXThisExpr`) and
`tools/clang/lib/Sema/SemaExprCXX.cpp`'s `genereateHLSLThis` (HLSL's `this` is rewritten from
`T*` to an lvalue of type `T`, unlike standard C++, so returning `this` by value is an
**aggregate** expression, not a pointer load).

Because the maintainer comment specifically claims a cross-backend difference (SPIR-V works,
DXIL does not), a same-source `-spirv` control is part of the required evidence, not optional
extra credit — this is the "contrasting compiler reaching the capability from the same source"
kind of check the skill calls for before accepting an absence/difference claim.

## What would falsify "still reproduces"

- The same repro (`-T cs_6_0 -E main`, DXIL, no `-spirv`) compiling **cleanly** on `main-debug`,
  emitting a correct struct copy, with no `cannot compile this ... yet` diagnostic and exit 0.

## Not-compiler-verifiable aspects

None expected — this is a pure front-end/CodeGen compile-time question, fully answerable by
`dxc` alone; no GPU/runtime/driver evidence is needed.
