> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5987](https://github.com/microsoft/DirectXShaderCompiler/issues/5987).

Still reproduces on `main` (Debug build, commit 89e2f98e2).

Compiling the repro with `-T as_6_7 -E main` crashes an assert-enabled build:

```
Error: 	!(onlyUsedByLifetimeMarkers(BCI))
File:
lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp(2630)
Func:	`anonymous-namespace'::SROA_Helper::RewriteBitCast.
	expected struct bitcast to only be used by lifetime intrinsics
```

On a Release-style build (no asserts compiled in), this surfaces as the reporter's exact
`error: llvm::cast<X>() argument of incompatible type!` — reproduced verbatim starting at
v1.7.2207, the oldest stable release that can even compile the `as_6_7` profile. Every
release before that rejects the profile outright (`invalid profile as_6_7`) rather than
avoiding the bug, so the history is: unmeasurable until `as_6_7` existed, then always
crashing since. [Compiler Explorer](https://godbolt.org/z/YoavsEvns) confirms the crash on a
current trunk build as well.

Both workarounds mentioned in the report were re-verified and do avoid the crash: commenting
out `payload.data = blah;`, and "unwrapping" `payloadType` so its members aren't a nested
struct — both compile cleanly. So the trigger is specifically assigning a whole struct value
into a member that is itself a struct, inside a `groupshared` amplification-shader payload.

Suggested labels: current `bug, dxil, crash` already fit; no change proposed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
