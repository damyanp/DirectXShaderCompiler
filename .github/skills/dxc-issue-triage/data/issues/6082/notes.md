# Notes: #6082 — Incorrect DXIL bitcasts generated for bool matrices in ray payloads

## Ground truth

Compiler `main-debug` registered at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(`dxc --version`: `1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`), a
clean Debug build. `git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD --
. ':!.github/skills/dxc-issue-triage'` is empty, confirming the local working tree matches
the cited commit outside the skill directory.

## What was measured

Repro (`repro.hlsl`) is the exact source from the issue body. Command (`cmd.txt`):
`-T lib_6_6 repro.hlsl`. This is a code-generation-shape question, not a crash: `expected.md`
defines "reproduces" as DXC still emitting a pointer bitcast from the bool-matrix-backed
field to a `<N x i32>*`, followed by a `load <N x i32>` through that pointer (`match.json`,
a `regex` predicate anchored on the literal type name `class.matrix.bool` DXC emits for bool
matrices, paired with the bitcast→load sequence and matching vector width).

`out-main-debug.txt`: `main-debug` reproduces byte-for-byte the IR quoted in the issue —
`%class.matrix.bool.1.2 = type { [1 x <2 x i1>] }`, then
`bitcast %class.matrix.bool.1.2* %1 to <2 x i32>*` / `load <2 x i32>, <2 x i32>* %2, align 4`.

**Control (`control-boolvector.hlsl`, `--expect no-match`, `variant-boolvector-main-debug.txt`):**
a `bool2` *vector* (not matrix) payload field, same shape otherwise. It compiles to
`%struct.MyPayload = type { <2 x i32>, i32 }` with a plain `load i32` off a GEP — no bitcast,
no wider-vector reinterpretation. This confirms the reporter's own observation that bool
*vectors* already avoid the pattern by using an `i32` representation directly, and that the
predicate discriminates rather than matching everything.

**DXC's own validator accepts the output.** `dxc -T lib_6_6 repro.hlsl -Fo out.dxil` exits 0
with no validation errors or warnings — consistent with the maintainers' position (below) that
this is valid DXIL under DXC's own (non-standard) interpretation of vector layout, even though
it is not valid under the plain LLVM LangRef.

## History

```
python scripts/triage.py bisect --issue 6082
```

`v1.4.1907` and `v1.5.2010` are `invalid-probe`: both answer `error: invalid profile lib_6_6`
(`out-v1.4.1907.txt`, `out-v1.5.2010.txt`) — `lib_6_6` did not exist yet, so neither release
ever reached the code under test. `v1.6.2104` (2021-04-20, the oldest release that accepts
`lib_6_6`) already reproduces byte-for-byte identically to `main-debug` except for
inlined-natured debug/version metadata differences (`out-v1.6.2104.txt`). `v1.9.2607`
(2026-07-29, newest cached release) also reproduces (`out-v1.9.2607.txt`). Result:
**always-repro'd across v1.6.2104..v1.9.2607** — the effective bisection floor for this issue
is v1.6.2104, not the usual v1.4.1907 floor, because `lib_6_6` postdates it. 5 prereleases
were excluded from the search by policy (none of them named in the issue text).

Compiler Explorer corroborates both ends of what CE can see:
`dxc_1_6_2112` (CE's oldest DXC) and `dxc_trunk` both emit the identical
`bitcast %class.matrix.bool.1.2* ... to <2 x i32>*` / `load <2 x i32>` sequence
(`manual-case-godbolt-verify.txt`). Link: https://godbolt.org/z/zxjbnx5dE

## The thread's real content is a design dispute, not an open repro question

The reported IR shape is uncontested and unchanged; what is contested is whether it is a bug.
Reading the seven comments in order:

- **jasilvanus** (reporter): the DXIL data layout string's `i1:32` alignment is irrelevant to
  vector *element* packing per the LLVM LangRef — vectors are always bit-packed — so the
  bitcast-to-`<N x i32>` assumes a 32x wider layout than the `<N x i1>` it's reinterpreting.
- **llvm-beanz** (DXC maintainer): pushes back that DXIL is a *serialized* LLVM module but is
  not meant to be reinterpreted as standard/modern LLVM IR; DXIL's per-type layout rules are
  DXIL-specific and diverge from the LLVM LangRef DXC's own bitcode was forked from (3.7). The
  failure only manifests when third-party tooling re-parses DXIL as modern LLVM IR and runs
  generic LLVM passes over it — which is exactly what the reporter does in comment 4
  (`opt -passes="vector-combine,instcombine"` from an upstream LLVM build, not from DXC),
  producing an out-of-bounds GEP after the "fixed" layout is combined with generic vector
  folding.
- **llvm-beanz** again: describes an actual planned resolution — a set of transformations,
  as part of the new LLVM-based HLSL/DXIL codegen work, to convert DXIL into valid modern LLVM
  IR (including over-aligned vector elements and per-address-space layout rules), rather than
  changing this DXC's (the C++/LLVM-3.7-fork repository under triage) own codegen.
- **damyanp** (maintainer, 2024-04-10, the last comment): says the team still needs internal
  discussion and asks tex3d to weigh in. No further comment or linked PR since.

The issue's single cross-reference (`gh api .../timeline`) is
`llvm/llvm-project#91639` ("[HLSL] Boolean vector support", 2024-05-09), in the upstream LLVM
tree where the new Clang-based HLSL frontend lives — consistent with llvm-beanz's stated
direction of doing this work in the new frontend rather than in this repository. No PR against
*this* repository (DirectXShaderCompiler) references #6082.

## Assessment

The reported code shape reproduces unchanged, on every probeable release and on `main`, and
is corroborated on Compiler Explorer's oldest and newest DXC. This is not in dispute. What
remains genuinely open — and unresolved since 2024-04-10 — is whether it constitutes a DXC
bug at all, given DXC's position that DXIL's per-type layout semantics are its own and that
the failure mode the reporter demonstrates requires treating DXIL as portable modern LLVM IR,
which DXC does not claim to produce. This triage does not and cannot settle that design
question; it can only confirm the shape is unchanged and that no resolution has landed.

`--triaged-with-commit 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, `--triaged-by
"GitHub Copilot CLI"`, `--reviewed-by` pending (step 10's cross-model review is batch-level
work, not performed in this single-issue session).
