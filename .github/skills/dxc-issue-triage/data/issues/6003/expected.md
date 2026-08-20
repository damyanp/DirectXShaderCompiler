# Expected behavior for #6003

Repro quality: **complete** (both asks have a verbatim command + shader from the issue body;
the second ask additionally cites an exact file:line in dxc's own source).

The issue bundles two independent findings from a Valgrind memcheck run against a Linux debug
build of dxc compiling:

```
valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes dxc -T lib_6_4 -spirv \
  -fspv-target-env=vulkan1.2 -enable-16bit-types -HV 2021 -O0 -Zi shader.hlsl -Fo shader.spv
```

with `shader.hlsl` = a `raygeneration` shader calling `Texture2D::SampleLevel`.

**Ask 1 (open, general):** Valgrind reports "Conditional jump or move depends on
uninitialised value(s)" in `clang::TypeLoc::getBeginLoc() const (TypeLoc.cpp:195)`, reached
through `TreeTransform<TemplateInstantiator>::TransformType` while instantiating a `FieldDecl`
of the synthetic HLSL vector template (`GetOrCreateVectorSpecialization` /
`NewSimpleAggregateType` in `SemaHLSL.cpp`, called from `HLSLExternalSource::LookupVectorType`).
The reporter's own second comment (sudonatalie, 2023-11-21) says this branch is also reached
compiling to DXIL, so it is not SPIR-V-backend-specific — it is a Sema/AST-instantiation issue.
"Reproduces" for this ask means: a Valgrind/memcheck run (or equivalent sanitizer with
uninitialized-value detection, e.g. MSan) on a debug build still reports a conditional-jump
warning at or attributable to `TypeLoc::getBeginLoc()` for this call chain.

**Ask 2 (narrower, already resolved per the reporter):** a separate memcheck report of an
out-of-bounds/uninitialized-index array read at `SemaHLSL.cpp:6465` —
`if (Template[pIntrinsic->pArgs[0].uTemplateId] == AR_TOBJ_OBJECT)` — in
`HLSLExternalSource::MatchArguments`. The issue body states this line "has been already fixed
on the main branch" as of the reporter's own check against a Nov-2023 `main` (hash
`ceff9b804`), reproducing only against the `v1.7.2308`-sourced build. "Reproduces" for this ask
means the array index used at that call site is not bounds-checked against `MaxIntrinsicArgs`
before the `Template[...]` read.

**What we can and cannot measure here:** Valgrind/memcheck (and any Linux tooling) is not
available in this Windows environment, and no rebuild of dxc is permitted for this triage,
so ask 1 cannot be directly re-confirmed or refuted by running the tool that detects it. Ask 2
is a specific, quotable line of source and can be checked by reading `SemaHLSL.cpp` at the
ground-truth commit, and by tracing `git log` for the fix the reporter refers to.
