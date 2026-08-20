# Expected symptom — #4858 "[DXIL] Illegal code motion for CalculateLevelOfDetailUnclamped"

**Reported (2022-12-08):** for the shader below, `dxc test.frag -Tps_6_0` (implicit `-E main`)
emits DXIL/LLVM IR in which the `dx.op.calculateLOD` call implementing
`Texture2D::CalculateLevelOfDetailUnclamped` has been sunk out of the shader's unconditional
entry block and into the true-arm of an `if (all(uv < 0.5))` branch. The reporter's claim is
that this is **illegal code motion**: `CalculateLevelOfDetailUnclamped` (like an implicit-derivative
sample) requires uniform execution across a quad to compute a correct level of detail, so moving
its evaluation into non-uniform (divergent) control flow is undefined behaviour, independent of
whether the returned value is later used only inside that same divergent block.

A 2024-09-26 maintainer comment asked whether this is actually undefined, given the LOD input
comes from a `uv` varying rather than an implicit-derivative source; the reporter replied that
scaling `uv` first (so the sunk value differs from what would have been computed at block entry)
doesn't change the sinking, and posted a second shader using `sin(uv)` that shows the same
sinking.

**Repro quality:** `complete` — the issue supplies a full, minimal pixel shader and quotes the
exact miscompiled IR.

**What we test:** compile the supplied shader as `ps_6_0` (`-E main`) with an assert-enabled
Debug build of `main`, and inspect the emitted DXIL/LLVM-IR text.

**Symptom is present if:** the disassembly shows the `dx.op.calculateLOD` call placed inside the
label block reached by the *true* arm of a conditional branch (`br i1 ..., label %true, label
%false`), rather than in the entry block before that branch — i.e. the LOD calculation has been
sunk into non-uniform control flow relative to how the source was written (an unconditional
`CalculateLevelOfDetailUnclamped` call followed by a divergent `if`).

**Symptom is absent if:** `dx.op.calculateLOD` appears only in the unconditional entry block
(before any `br i1`), matching the control-flow-independent placement the source implies, or the
compiler diagnoses the construct instead of silently miscompiling it.

**Not compiler-verifiable:** whether the *result* of `CalculateLevelOfDetailUnclamped` after
sinking is numerically wrong on real hardware is a GPU/driver-level claim about implicit-derivative
uniformity that this tool cannot check. What DXC's own IR can show, and what this triage measures
instead, is the structural fact the issue actually screenshots: whether the code-motion happens at
all in the compiled IR. That structural question is decidable from `dxc`'s output alone.
