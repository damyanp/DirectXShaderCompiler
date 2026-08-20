# Expected symptom

Filed by @bob80905 (Joshua Batista) on 2023-07-22T01:12:41Z, six minutes after
their own PR [#5399](https://github.com/microsoft/DirectXShaderCompiler/pull/5399)
("Prevent instructions that accept handle arguments from accepting malformed
handle arguments") merged. Labelled `enhancement`, `tech-debt`, `diagnostic`,
`validation`. This is a follow-up tech-debt request about the *organization*
of `lib/DxilValidation/DxilValidation.cpp`, not a report of a specific
miscompile or crash.

The issue describes a specific mess in the validator, in its own words:

1. `GetResourceFromHandle` both looks up a handle's resource properties *and*
   emits validation errors as a side effect (`InstrHandleNotFromCreateHandle`,
   the SM6.9 `InstrReorderCoherentRequiresSM69` check).
2. Because of (1), any downstream code that calls `GetResourceFromHandle`
   again to look up the same handle's properties for op-specific validation
   (the issue names `GetSamplerKind`, `GetResourceKindAndCompTy`,
   `GetCBufSize`) re-emits the same error for an already-flagged invalid
   handle -- a spurious duplicate diagnostic.
3. `GetResourceFromVal` exists as a silent counterpart with no error-emitting
   side effect, but is used inconsistently alongside `GetResourceFromHandle`.
4. The requested fix: rename `GetResourceFromHandle` into a
   validation-only, up-front `ValidateResourceHandle()`-style function (run
   once per handle argument); change the three named accessor functions,
   and every other caller that currently uses `GetResourceFromHandle` for a
   properties lookup, to call `GetResourceFromVal()` and check `IsValid()`
   before using the properties, so no downstream error is emitted for a
   handle already flagged invalid.

**"Reproduces" means:** the codebase at ground truth still has this
architecture unchanged -- `GetResourceFromHandle` (not renamed, still
error-emitting) is still called both from the up-front handle-argument pass
and from `GetSamplerKind`/`GetResourceKindAndCompTy`/`GetCBufSize` (or their
current equivalents), so an invalid handle reaching one of those ops still
produces the described duplicate diagnostic architecture; no
`ValidateResourceHandle` function exists; and resource-property call sites
are not uniformly guarded by `isValid()`.

**"Does not reproduce" would mean:** the rename/reorganization described has
happened -- `GetResourceFromHandle` (or a `ValidateResourceHandle`
equivalent) is validation-only and called exactly once per handle argument,
and every other call site uses the silent accessor guarded by a validity
check.

This is a request to reorganize internal validator source code, not a
report of a specific input producing wrong compiler behaviour, so there is
no single `dxc.exe` command line whose output either confirms or refutes it
directly. The one concrete, externally observable consequence named in the
issue -- a duplicate diagnostic for the same invalid handle -- is,
by construction, only reachable with a malformed DXIL resource handle (a
`CallInst` operand of the handle type that is not a recognised
`CreateHandle`/`AnnotateHandle` result). Per the skill's guidance for
capability/organization questions, the primary evidence is source inspection
of the validator itself, corroborated by the file's commit history and by a
control probe establishing why an ordinary HLSL-driven `dxc.exe` repro cannot
reach that path (see `source-evidence.txt`).

Repro quality: **complete** -- the issue names the exact functions
(`GetResourceFromHandle`, `GetResourceFromVal`, `GetSamplerKind`,
`GetResourceKindAndCompTy`, `GetCBufSize`, `IsValid()`) and the exact desired
end state, so every claim it makes about the current code is checkable
verbatim against source, without needing to guess at scope.
