# #4619 — How to get thread group size and output primitive topology in MeshShader?

**Verdict: `repros`, but only half of it, and the interesting half is what
happened to the other one.**

The issue asks two things. They have opposite answers, and neither answer has
ever reached the thread:

| ask | today, on `main` (`13730886e`) | status |
|---|---|---|
| A. `ID3D12ShaderReflection::GetThreadGroupSize` returns `0,0,0` for a mesh shader | returns the declared `32,2,1` | **fixed** in v1.7.2212, Oct 2022, by PR #4745 |
| B. no way to get the mesh output primitive topology | still nothing on `ID3D12ShaderReflection` | **repros**, and always has |

Ask A was a real bug and it was fixed **two months after this issue was
filed**, by a PR that never mentioned the issue. The issue therefore stayed
open with zero comments, was labelled `enhancement` + `reflection` in January
2024 — fifteen months *after* the fix shipped — and was milestoned to Backlog
in September 2024. Nothing in the thread says that half of it is done.

Ask B is a genuine, still-open gap, but it is a gap in the **API surface**, not
in the compiler: the topology is in the container (PSV0 and DXIL metadata),
just not reachable through `ID3D12ShaderReflection`. That is
`enhancement-not-bug`, which is what the existing labels already assert —
except that until now nobody had measured it.

## The hazard in this issue, and how the evidence resolved it

The brief warned that a question-shaped title invites a forced, bug-shaped
verdict, and that "still reproduces" may be the uninteresting half. Both were
live risks here and the evidence settled them:

* Scoring the issue as one thing would have been wrong either way. Called
  `does-not-repro` (because thread group size works now) it would have dropped
  a real open request. Called `repros` without decomposition it would have
  implied `GetThreadGroupSize` is still broken, which would be false and would
  send a maintainer looking for a bug that was fixed in 2022.
* The useful finding really is the **fate of the resolution**, not the repro.
  The repro half is four lines of matrix. The finding is that a merged fix and
  its issue were never connected, so the issue's own record is wrong about its
  own state, and every human who has touched it since has been working from
  that wrong record.

## What was measured, and why it needed a harness

Both asks are about return values from a COM interface that `dxc.exe` never
calls, so no `cmd.txt` + `match.json` pair over `dxc.exe` output can reach the
code under test.

`dxa -dumpreflection` was tried first, as SKILL.md directs, and it cannot
answer either half. This is captured in
**`manual-case-dxa-dumpreflection.txt`** rather than asserted:

* `D3DReflectionDumper.cpp` contains **zero** call sites for
  `GetThreadGroupSize`. The dumper never asks the question, so its silence is
  not an answer.
* It prints `GSOutputTopology` only inside its `ShaderKind == Geometry` branch
  (`D3DReflectionDumper.cpp:164`); its mesh branch (`:180`) prints one line,
  about `PatchConstantParameters`.

This is exactly SKILL.md's "an absent field proves nothing if it never calls
the accessor", so the dump is evidence about the *dumper*, not about the
reflection API.

`refl4619.cpp` (in this directory) is a small C++ program that does what the
reporter's application does:

    IDxcCompiler::Compile(source, -T ms_6_5)
    IDxcContainerReflection::Load / FindFirstPartKind(DXIL)
    GetPartReflection(idx, IID_ID3D12ShaderReflection)
    ID3D12ShaderReflection::GetDesc          <-- every topology-ish field
    ID3D12ShaderReflection::GetGSInputPrimitive
    ID3D12ShaderReflection::GetThreadGroupSize   <-- the reported 0,0,0

and then reads the *same two facts* out of the container by a second,
independent route that does not go through the reflection interface at all:
the PSV0 part (`PSVRuntimeInfo1::MS1.MeshOutputTopology`,
`PSVRuntimeInfo2::NumThreadsX/Y/Z`) and the DXIL disassembly's
`!dx.entryPoints` mesh-state tag. That second route is what makes the
measurement mean "the API does not surface it" rather than the much bigger
claim "the compiler does not record it".

It loads whatever `DXC_REFLECT_DLL` names, so pointing it at a release's
`dxcompiler.dll` measures **that release's** reflection code. Registered as the
compiler `main-debug-refl4619` via `run-refl4619.cmd`, so `triage.py run`,
`--shader`/`--args` controls, `--expect` and re-scoring all work normally.
Harness-as-compiler pattern, following #3237.

**Nothing binary is committed.** `bin/`, `bin-build.log` and `scratch-*.dxil`
are excluded by `.gitignore` in this directory; what is committed is the
harness source, its build script and the wrapper, which rebuilds on demand. To
rebuild by hand:

    cd data/issues/4619 && ./build-refl4619.cmd

All committed artifacts use the `<cache>` / `<triage>` / `<repo>` placeholders
`triage.py` writes in its capture headers. Both writers redact: `refl4619.cpp`
has a `Redact()` for the lines it prints, and the three `measure-*.py`
generators call `triage.redact_paths()`. `triage.py` only redacts the lines
*it* writes — a harness's stdout passes through untouched.

## Ground truth — `main-debug`, 1.9.0.5433, `13730886e`

From `out-main-debug-refl4619.txt` and
`out-main-debug-refl4619--match-topology.txt`:

    RESULT: GETTHREADGROUPSIZE=32,2,1 GETTHREADGROUPSIZE-RETURN=64
      SHADERDESC-TOPOLOGY-FIELDS=GSOutputTopology:0,InputPrimitive:0,
        HSOutputPrimitive:0,TessellatorDomain:0,GSInputPrimitive:0
      PSV-MESH-TOPOLOGY=2 PSV-NUMTHREADS=32,2,1
    PSV.RuntimeInfo1.MS1.MeshOutputTopology=2 (Triangle)

Read it as: ask A is fixed (`32,2,1`, return value 64 = 32×2×1); ask B
reproduces (every topology-shaped field of `D3D12_SHADER_DESC` is zero, while
the container plainly holds topology 2 = Triangle).

`repro.hlsl` declares `[numthreads(32,2,1)]` and `[outputtopology("triangle")]`
deliberately: the values are neither 1,1,1 nor all-equal, so a harness that
returns a constant, swaps components or reads the wrong entry point cannot
produce them by accident.

## Controls

Five, each run through `triage.py run --expect no-match`, all passing:

| control | what it would have caught | file |
|---|---|---|
| `control-compute.hlsl` — CS, same `[numthreads(32,2,1)]` | a broken harness/reader: if the *compute* case also read 0,0,0 the mesh result would mean nothing | `variant-compute-main-debug-refl4619.txt` |
| `control-amplification.hlsl` — AS, same numthreads | the sibling stage fixed by the same PR | `variant-amplification-main-debug-refl4619.txt` |
| `control-pixel.hlsl` — PS | that `0,0,0` is the **correct** answer for a non-thread-group stage; without the `shader-kind=Mesh` clause `match.json` would "reproduce" on every pixel shader ever compiled | `variant-pixel-main-debug-refl4619.txt` |
| `control-geometry.hlsl` — GS `TriangleStream` | that the harness can read a topology that *is* present, so ask B's zeros are absence and not a blind reader | `variant-geometry-topology-main-debug-refl4619.txt` |
| `control-mesh-line.hlsl` — `[outputtopology("line")]` | that the PSV reading tracks the declaration rather than printing a constant 2 | `variant-mesh-line-topology-main-debug-refl4619.txt` |

The geometry control is the load-bearing one for ask B. An all-zero
`D3D12_SHADER_DESC` is what you also get from a harness that forgot to call
`GetDesc`; the GS control produces a non-zero `GSOutputTopology` through the
identical code path, so the mesh zeros are a real absence.

## History — fixed-harness release matrix, not `bisect`

**`bisect` must not be run on this issue** and was not. It resolves each tag to
that release's `dxc.exe`, which never calls `ID3D12ShaderReflection`; every
release would score `no-repro` and it would confidently report the inverse of
the truth. This was pre-registered in `expected.md` before anything ran.

`measure-history.py` instead holds the *reader* fixed and varies
`DXC_REFLECT_DLL` across every cached stable release. Output:
**`manual-case-release-history.txt`**, 20 releases × 2 cases.

Ask A:

* `v1.4.1907` — **invalid probe**, not a data point: `error: invalid profile
  ms_6_5`, exit 2, harness reports `WALK-INCOMPLETE`. The compute control on
  the *same DLL* returns `32,2,1`, which is what proves the rejection is the
  absence of mesh shaders in that release and not a fault in the harness.
* `v1.5.2010`, `v1.6.2104`, `v1.6.2106`, `v1.6.2112`, `v1.7.2207` — **5
  releases**, mesh `0,0,0` beside compute `32,2,1`. Exactly the reported
  symptom.
* `v1.7.2212` (2022-12-16) through `v1.9.2607` (2026-07-29) — **14 releases**,
  mesh `32,2,1`.

A single, clean, monotonic transition between v1.7.2207 and v1.7.2212. Note
that **v1.7.2207 is the release current when the issue was filed** (2022-08-26)
and it reproduces, so the reporter's own observation is confirmed rather than
doubted.

Ask B: `SHADERDESC-TOPOLOGY-FIELDS` is all-zero on **all 39 rows** — every
release, both shader kinds, and `main`. `GSOutputTopology` is never non-zero
anywhere in the matrix. Meanwhile `PSV-MESH-TOPOLOGY=2` on all 19 mesh rows,
i.e. from the first mesh-capable release onward. Never worked, never regressed.

## Attribution of the ask-A fix

Captured in **`manual-case-resolution-fate.txt`**:

* `git log -S "IsMS()" -- lib/HLSL/DxilContainerReflection.cpp` returns exactly
  one commit: `80fb4622a`, "Made shader reflection return thread group size for
  AS and MS (#4745)", Adam Yang, 2022-10-27.
* Its diff is precisely the guard the symptom implies: `if (!IsCS())` became
  `if (!IsCS() && !IsMS() && !IsAS())`, plus 88 lines of new test in
  `CompilerTest.cpp`.
* `git merge-base --is-ancestor 80fb4622a v1.7.2207` → exit 1 (absent);
  `... v1.7.2212` → exit 0 (present). The commit lands inside the exact window
  the matrix brackets.
* That window holds 156 commits, of which **4** touch the reflection
  implementation; the other three are `Fallthrough (#4843)`, `Fill in
  RequiredFeatureFlags in library function reflection (#4774)` and `[linux]
  Enable Reflection on *nix platforms (#4810)`, none of which is about thread
  group size.

Attribution is **strong but not built-at-the-commit**: I did not compile
`80fb4622a` and its parent. The identification rests on the guard being the
only `IsMS()` change ever made to that file, the diff matching the symptom
exactly, and the release boundary agreeing. Naming the commit is safe;
"nothing else in the window could have done it" is inference.

## The resolution fate — the actual finding

Also in `manual-case-resolution-fate.txt`, all read-only GitHub calls:

* PR #4745 is `MERGED`, 2022-10-27, `closingIssuesReferences: []` — it closes
  nothing.
* A repo-wide search for `GetThreadGroupSize` returns exactly two objects:
  issue #4619 and PR #4745. There is no edge between them.
* The issue's full timeline: `needs-triage` (2023-06-29), swapped for
  `reflection` + `enhancement` (2024-01-18), milestoned Backlog (2024-09-30).
  **No cross-reference event of any kind.**
* Comment count: **0**.

So the fix shipped, and the record of the issue never learned about it. Both
subsequent triage passes were made against a state that had been obsolete for
over a year.

## Source corroboration

* `lib/HLSL/DxilContainerReflection.cpp:2752` — `GetThreadGroupSize` guards on
  `IsCS() || IsMS() || IsAS()` today.
* `lib/HLSL/DxilContainerReflection.cpp:2489` — `pDesc->GSOutputTopology =
  M.GetStreamPrimitiveTopology()`, unconditionally, for every stage.
* `lib/DXIL/DxilModule.cpp:846` — `m_StreamPrimitiveTopology` is assigned only
  from geometry-shader properties, so it stays `Undefined` for a mesh shader.
  That is the mechanical reason ask B reads zero: not a mesh-specific bug, just
  a GS-shaped field being read on a non-GS stage.
* `external/DirectX-Headers/include/directx/d3d12shader.h:115` —
  `D3D12_SHADER_DESC` has **no** mesh-specific member. Ask B cannot be fixed by
  populating an existing field; it needs new API surface. This is the ABI-level
  reason it is an enhancement and not a bug.
* `include/dxc/DXIL/DxilFunctionProps.h:164` — MS properties do carry
  `outputTopology`, and `DxilConstants.h:2046` defines
  `MeshOutputTopology { Undefined=0, Line=1, Triangle=2 }`. The data exists all
  the way through; only the public surface stops short.
* `include/dxc/DxilContainer/DxilPipelineStateValidation.h:104` —
  `PSVRuntimeInfo1::MS1.MeshOutputTopology`, which is the workaround.

## Compiler Explorer

<https://godbolt.org/z/oT63zTbMf> — `dxc_trunk`, `-T ms_6_5 -E main`.

Published with a `godbolt-note.txt` that says plainly what the pane can and
cannot do. **CE cannot demonstrate either half of the issue**: its panes run
`dxc.exe`, which never calls `ID3D12ShaderReflection`. A skip would have been
defensible on those grounds. I published anyway because the pane *can* show
the presence side of the workaround, which is the part the reporter can act
on — the mesh-state entry-point tag with its five fields, thread group size and
output topology among them, verified in `manual-case-godbolt-verify.txt` to
appear in generated output and not in the embedded banner:

    !61 = !{i32 9, !62}
    !62 = !{!63, i32 3, i32 1, i32 2, i32 0}
    !63 = !{i32 32, i32 2, i32 1}

Field order confirmed against `DxilMetadataHelper.h:367-371`
(`NumThreads`, `MaxVertexCount`, `MaxPrimitiveCount`, `OutputTopology`,
`PayloadSizeInBytes`) — so `32,2,1` / maxverts 3 / maxprims 1 / **topology 2 =
Triangle** / payload 0, matching the two attributes in `repro.hlsl` exactly.

## Predicates

`match.json` (ask A) and `match-topology.json` (ask B). Two design points worth
recording:

* Ask B's absence is expressed as a **positive `contains`** on the exact
  rendered `SHADERDESC-TOPOLOGY-FIELDS=...` line, never as `not_contains`. A
  `not_contains` would be satisfied for free by a compile that failed before
  producing any output at all.
* Ask A's anti-vacuity anchor is an `any_of` over **two independent container
  witnesses** — the DXIL numthreads metadata tuple, or `PSV-NUMTHREADS`. This
  turned out to be load-bearing: v1.5.2010 and v1.4.1907 emit
  `PSV.RuntimeInfoVersion=1`, which has no `NumThreadsX/Y/Z` (those arrive with
  RuntimeInfo2 at v1.6.2104). Requiring **both** witnesses would have silently
  demoted the oldest mesh-capable release to "couldn't tell", and the earliest
  edge of the history is exactly where the interesting boundary is.
* `match.json` is scoped to `shader-kind=Mesh`, because `0,0,0` is the correct
  answer for VS/PS/GS. `control-pixel.hlsl` exists to demonstrate that the
  unscoped predicate would have "reproduced" on every pixel shader.

## How the verdict fields were filled

An issue with two asks and two histories has to be compressed into a schema
that holds one of each. The compression is a judgement call, so it is recorded
here rather than left implicit in the row.

* **`status = repros`** scores **ask B**, the half that is still open. Ask A is
  fixed, so scoring the issue `does-not-repro` would have silently dropped a
  live request; scoring ask A would have implied `GetThreadGroupSize` is still
  broken, which is false and would send a maintainer hunting a 2022 bug.

* **`history = always-repro'd`** follows from that choice. `history` is a
  taxonomy slot describing the *scored* symptom, and ask B has never worked on
  any release that could be measured: all 39 rows of the 20-release matrix show
  every topology-shaped `D3D12_SHADER_DESC` field zero. It never regressed and
  was never fixed, so `always-repro'd` is the only one of the four accepted
  values that fits.

  The two alternatives were considered and rejected. `fixed-in v1.7.2212` is
  true of **ask A** but not of the issue, and putting it in the slot would
  publish "this issue was fixed" to every table and query that reads the field.
  `never-repro'd-in-releases` is wrong in the other direction: it means the
  releases could not show the symptom, whereas here every release showed it.
  Ask A's history is not lost — it is stated in the table at the top of this
  file, measured in the History section, and attributed below.

* **`fixed_in` deliberately left unset.** It is an issue-level field, and the
  issue as a whole is not fixed. Ask A's fix release (v1.7.2212) is recorded in
  prose here and in `--summary`; asserting it in the machine-readable field
  would make #4619 appear in a "fixed, can be closed" query, which is exactly
  the mistake the resolution-fate finding is about.

* **`text_stale` set**, in the inverted sense: the body's factual claim is now
  *too pessimistic* rather than understating a live defect. Either way a reader
  who trusts the text over the compiler is misled, which is the harm the field
  exists to flag.

## What I could not measure, and what I got wrong

* **Not built at `80fb4622a`.** See attribution above.
* **Not measured on a real D3D12 runtime.** Everything here is DXC's own
  reflection implementation in `dxcompiler.dll`. If the reporter was using the
  OS `D3DReflect` rather than DXC's, the version that matters is their
  `dxcompiler.dll`, not their Windows build — but I have not verified how the
  two agree, and I have not said so in the draft comment as though I had.
* **Ask B's "no member returns it" is a claim about the members I called.** I
  called `GetDesc`, `GetGSInputPrimitive` and `GetThreadGroupSize`, and read
  the `d3d12shader.h` struct definition to check there is no mesh field. I did
  not exhaustively call every method of `ID3D12ShaderReflection`. The header
  reading is what carries the claim; the harness corroborates it.
* **A counting error, corrected.** Mid-investigation I recorded the broken
  window as 6 releases. It is **5** (v1.5.2010, v1.6.2104, v1.6.2106,
  v1.6.2112, v1.7.2207); v1.4.1907 is an invalid probe, not a sixth broken
  release, and conflating the two would have overstated the history. Every
  count published here was re-derived from the SUMMARY table in
  `manual-case-release-history.txt` rather than from earlier prose.
* **Nothing was posted to GitHub.** `comment.md` is a draft. All `gh` use was
  read-only.
