# Triage — #4858 [DXIL] Illegal code motion for CalculateLevelOfDetailUnclamped

| | |
| --- | --- |
| Opened | 2022-12-08 |
| Labels | `bug`, `correctness`, `check-in-clang` |
| Repro quality | **complete** (full shader supplied in the issue, plus a second confirming variant in a comment) |
| Status vs `main` | **repros** |
| History | **always-repro'd** (v1.4.1907 → v1.9.2607, linear scan, no fix/revert window) |
| Confidence | **high** |
| Suggested action | **still-valid-keep-open** |

## What the issue reports

The supplied shader computes `T.CalculateLevelOfDetailUnclamped(S, uv)` unconditionally, then
branches on `all(uv < 0.5)` and only *uses* the LOD value inside that branch. The reporter's
claim is that DXC's compiled IR sinks the `CalculateLOD` op itself into the branch's true arm —
not just the arithmetic that consumes it — which moves a sampler-derivative-class operation into
non-uniform control flow. A 2024-09-26 maintainer comment asked whether this is really UB, given
the LOD is fed from a `uv` interpolant rather than an implicit screen-space derivative; the
reporter replied that scaling the input first doesn't change the sinking, and posted a second
shader using `sin(uv)` in place of `uv` that shows the same behaviour.

## What was tested

`repro.hlsl`, verbatim from the issue body, compiled `-T ps_6_0 -E main` (the issue's own
`dxc test.frag -Tps_6_0`, made explicit).

## Predicate

`match.json` is a structural regex: symptom present when the DXIL/LLVM-IR disassembly places
the `dx.op.calculateLOD` **call** inside the specific label block named as the *true* successor
of a `br i1` (bounded so it cannot walk past that block's own end into the file's trailing
`declare float @dx.op.calculateLOD.f32` line — see `method-notes.md` for why that bound is
load-bearing). This directly tests the structural fact the issue itself screenshots, rather than
a downstream consequence of it.

**Controls, all captured and re-checkable:**

| capture | what it shows | expect | result |
| --- | --- | --- | --- |
| `out-main-debug.txt` (primary) | ground truth, exact repro | — | **repro** |
| `variant-sin-variant-main-debug.txt` | reporter's second (`sin(uv)`) shader, same repro args | match | **repro** — confirms the second report, not just the first |
| `variant-control-od-main-debug.txt` | same `repro.hlsl`, `-Od` added | no-match | **no-repro** — `-Od` disables the sinking pass entirely; `calculateLOD` lands in the unconditional entry block (verified by inspection: `%6 = call float @dx.op.calculateLOD...` precedes `br i1 %12, label %13, label %21`). This is the control that proves the predicate discriminates sunk-vs-not-sunk, not merely "does the file mention calculateLOD" |
| `variant-control-no-lod-main-debug.txt` | unrelated shader with an `if` but no `CalculateLevelOfDetailUnclamped` at all | no-match | **no-repro** — anti-vacuity: the predicate does not fire on branches in general, only on this specific sinking |

## Result — reproduces in every stable release checked, and on `main`

```bash
python scripts/triage.py bisect --issue 4858 --linear
```

Every one of the 20 probeable stable releases from **v1.4.1907** (2019-07, the bisection floor)
through **v1.9.2607** (2026-07) scores `repro`; five prereleases were correctly excluded by
policy. Both binary-search endpoints agreeing was itself only weak evidence (a fix-then-revert
window would look identical at the endpoints), so a full `--linear` scan was run to rule that
out explicitly — every intermediate release also shows the sinking, so there is no hidden
fixed/regressed window. `CalculateLevelOfDetailUnclamped` and DXIL sinking-style codegen are both
old enough that no release is `invalid-probe` here.

## Ground truth build

`main` at `main-debug`, self-reporting `7665270b9` (`dxc --version`:
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`), registered
in `.cache/compilers/main-debug.json` with `git_commit: 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.
That self-reported SHA is fork-local and resolves nowhere upstream, so before trusting it this
session re-ran the equivalence check the registration record documents:

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df   # 5315 files, 0 outside .github/skills
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df~50 # CONTROL: 115 files outside .github/skills
```

The first diff touches only paths under `.github/skills/` (triage data from earlier batches);
the control against an older ancestor shows source files changing outside that tree, so the
comparison is capable of detecting a real difference and found none for the claimed commit. The
locally-built binary's DXC source is therefore source-equivalent to public upstream
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, which is the commit cited in this triage and in
`verdict.json`, not the fork-local `7665270b9` the binary prints.

## Compiler Explorer

<https://godbolt.org/z/1h4fff5Ef> — `dxc_1_6_2112` (CE's oldest DXC) and `dxc_trunk` both show
the same sinking: `br i1 %3, label %4, label %10` followed by `%5 = call float
@dx.op.calculateLOD.f32(...)` inside block `%4`, the branch's true successor — full text
archived in `manual-case-godbolt-verify.txt`. This corroborates the local Debug build's finding
on two independent (CE-hosted, Release, Linux) builds, one of which predates this triage's local
build by years.

**Clang pane attempted, inconclusive by construction, not by choice.** `hlsl_clang_trunk`
rejects the shader at Sema — `error: use of undeclared identifier 'InterlockedMin'` — because
Clang's HLSL front end does not yet recognise `InterlockedMin` as a free function on this path.
That failure is unrelated to the reported sinking and says nothing about whether Clang's
(separately-implemented, still-being-built) codegen would exhibit the same defect once it can
parse the construct at all. Confirmed reproducible with `gen-zi-sinking.py`, which compiles
`repro.hlsl` locally with the same `-Zi -Qembed_debug` flags CE always appends to DXC panes:
the sinking survives under those flags too (`if.then:` block contains the `calculateLOD` call,
reached only from the branch on line 8) — see `manual-case-zi-sinking.txt`. `match.json`'s regex
anchors on dxc's default *numeric* label naming and does not fire on this capture's
source-derived labels (`if.then`/`if.end`); that is a known, documented limitation of the
predicate, not a fixed result, which is why this capture is read by inspection rather than
scored.

**No compute-shader translation was built.** The construct (`Texture2D`/`RWTexture2D` handles,
implicit branch divergence, `SV_Target` output) is not stage-specific in principle, but Clang
already fails earlier than the stage-lowering boundary this translation exists to work around
(`InterlockedMin`, at Sema), so a compute restatement would not change what the Clang pane can
show and was not pursued.

## Assessment

The reported defect is real, reproduces identically in every stable release ever shipped and on
`main`, and is corroborated on two Compiler Explorer builds independent of the local build. It is
a genuine miscompilation risk if `CalculateLevelOfDetailUnclamped` (and by the same reasoning,
any implicit-derivative-requiring op) can legally be sunk past a divergent branch by a generic
LLVM code-motion pass without regard for the wave-uniformity requirements of the DXIL op it
computes — the compiler's own optimizer does not appear to treat `calculateLOD` (or the sibling
gradient-dependent ops) as pinned to its dominating block. Whether the *numeric result* differs
from what real hardware would compute for the un-sunk placement is a GPU/driver-level question
this tool cannot answer; what is directly measurable, and what this triage confirms, is the
structural fact the issue itself demonstrates: the code motion happens, on every build checked,
and nothing in the six years since filing has changed that.

The issue has been assigned (`tex3d`) and milestoned `Dormant` since 2024-09-26, the same day as
the last comment; there has been no further discussion since. `check-in-clang` remains a genuinely
open task — not yet answerable, not already answered — because the Clang front end cannot parse
this construct at all yet, for a reason unrelated to the bug under test.
