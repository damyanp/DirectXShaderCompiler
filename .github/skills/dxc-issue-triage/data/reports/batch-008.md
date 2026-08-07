# DXC issue triage — batch 008

**Ground truth:** clean `main` **Debug** build,
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`.
All five `verdict.json` files carry `triaged_with_commit: ab5400907`.
**History:** 20 official release binaries, v1.4.1907 → v1.9.2607, plus v1.5.2003 fetched by
hand for #2923.
**Nothing was posted, edited, labelled or closed. No DXC source was modified.**

> ### The ground-truth SHA no longer exists, and the build is still valid — verified by tree
>
> `main-debug` is registered at commit **`ab5400907`**, which the batch-007 commit-message
> rewrite replaced with **`950b58792`**. Collation re-verified rather than trusting the
> handover:
>
> ```
> git rev-parse ab5400907^{tree}   ->  574a2bd25a0b57ea1f450ea3dc0776919fcfe108
> git rev-parse 950b58792^{tree}   ->  574a2bd25a0b57ea1f450ea3dc0776919fcfe108
> git diff --name-only ab5400907 HEAD  ->  759 files, ALL under .github/skills/dxc-issue-triage/
>                                          0 files of compiler source
> ```
>
> Identical trees, and every difference to `HEAD` is inside the triage skill directory. The
> binary is a faithful `main` and **was not rebuilt**. `SKILL.md` now documents verifying
> provenance by tree rather than by SHA; this batch is the first to rely on it.
>
> Batches 005–008 all measure the same tree and are directly comparable. Batches 001–004
> measured `eff900d5` and are not.

> ### ⚠ Three process facts the orchestrator should read before committing
>
> 1. **`audit` does not re-score probes; only `reindex` does.** The brief and the orchestrator
>    notes both say `audit` "re-scores every probe ever captured, so a lesson learned late
>    reaches earlier issues", and instruct running it first for that reason. It does not:
>    `cmd_audit` checks completeness and overview staleness and reads existing verdicts.
>    `reindex` was correctly forbidden this batch, so **no retroactive re-scoring happened**.
>    Every method lesson promoted below reaches future batches only. `SKILL.md` has been
>    corrected.
> 2. **The review gate remains suspended**, as in 006 and 007. Nothing in `audit`,
>    `test_predicates.py` or the step-10 review checks whether a verdict is *true*.
> 3. **Unlike batch 007, this collation did change `scripts/` and `SKILL.md`.** Three carried-
>    over tooling items are implemented, with tests. See
>    [Carried-over tooling work](#carried-over-tooling-work).

## Headline

**One closable result, and it completes a five-and-a-half-year-old trio.** #2922 —
`value-to-declare` pass not handling the pointer case under `-O1` — **does not reproduce**, and
was fixed between v1.6.2112 and v1.7.2207. The evidence points to `c0676c7ca` (PR #4375,
Apr 2022), whose title matches the issue title, which edits the exact pass, and which deleted
all three `break; // don't run -O1 test until pointer types are dealt with by value-to-declare
pass` opt-outs from `PixTest.cpp`. **Attribution is strong, not proven**: the window holds 248
commits, three touching the file, and none was built in isolation. The worker wrote it that way
and the draft says so.

**The measurement did not come from `dxc.exe`, and could not have.** The fix is inside a PIX
pass no compiler driver runs. What makes #2922's verdict trustworthy is that each release's own
`dxcompiler.dll` was driven through `dxopt -external`, so the *pass* was bisected rather than
the compiler: at `-O1` it emits **0** `llvm.dbg.declare` on v1.6.2104/2106/2112 and **2** on
v1.7.2207 through `main`, on identical input, with the `B.CreateLoad(V)` that commit added
visible in the later output. The same technique carried #2923 in the opposite direction.

**#2923 is a regression, and its most useful finding is the one that weakens it.** Passing an
amplification payload struct *by value* to a subroutine leaves `main`'s own local mapped to six
PIX virtual registers that are never written, with the six member writes numbered onto the
inlined callee copy. It regressed at v1.6.2106 and is broken today. But at **v1.5.2003 — the
release current when the issue was filed** — the repro is numbered perfectly. The repro is
agent-constructed from the issue's own instruction, and the issue itself says *"Not clear yet
what set of structs are affected"*, so this may not be the reporter's 2020 instance. The draft
leads with the reproduction and states that caveat in full.

**#3377 has had two fixes attempted and both lapsed.** The access violation still fires on
`main` and on **all 20 releases** back to v1.4.1907 — eighteen months before the report, so
there is no version in which it worked. The trigger reduces to a semantic on a resource-typed
entry-point parameter: no matrix, no `SamplerState`, no second entry point, no `uniform`. PR
#4538 (Jul 2022) was closed unmerged in Mar 2024; PR #4554 (Jul 2022), whose body says *"This
was causing AV problems as described in #3377"*, was closed unmerged in Feb 2025 with *"Merge
conflicts, and according to @Tex3D it seems like this is the wrong direction"*. That is the
third instance of `SKILL.md`'s #2427 pattern — a confirmed-broken issue whose real finding is
what happened to the resolution.

**The other two reproduce and neither is a bug in the ordinary sense.** #3092 is a feature that
has never existed in any of the 19 SPIR-V-capable releases, and Clang trunk rejects it with
DXC's *first* diagnostic word for word (`error: 'numthreads' attribute requires an integer
constant`) — it is `enhancement-not-bug`, with one of the maintainer's three checklist items now
landed. #3693 is a missing front-end check: DXC *has* the "vector element index out of
bounds" diagnostic and never reaches it when the access is the index operand of another
subscript, so the element becomes `undef` and is used as a buffer index with validation passing.

**Two workers independently hit the same tooling trap, which is much stronger evidence than
one.** Both #3092 and #3377 wrote their own Compiler Explorer client because `godbolt` reports
only each pane's *first* line. Three workers independently started verifying short links via
`GET /api/shortlinkinfo/<id>`. Both are now in `triage.py`.

## Summary

| # | Title | Repro | Status | History | Action | CE |
| --- | --- | --- | --- | --- | --- | --- |
| [#2922](https://github.com/microsoft/DirectXShaderCompiler/issues/2922) | value-to-declare pass not handling pointer case under -O1 ⚠️ | prose-only | **does-not-repro** | **fixed between v1.6.2112 and v1.7.2207** | **close-fixed** | [End684Ycq](https://godbolt.org/z/End684Ycq) |
| [#2923](https://github.com/microsoft/DirectXShaderCompiler/issues/2923) | Structs passed to subroutines (can) cause the numbering pass to get confused about offsets of members | agent-constructed | **repros** | **regressed in v1.6.2106**; correct at v1.5.2003–v1.6.2104 | keep open | *(skipped — see below)* |
| [#3092](https://github.com/microsoft/DirectXShaderCompiler/issues/3092) | [SPIR-V] Allow thread group size to be specified with specialization constants | agent-constructed | **repros** (capability absent) | always; 19 SPIR-V-capable releases v1.5.2010→v1.9.2607; v1.4.1907 a genuine `invalid-probe` | enhancement, not a bug | [5dG5M5EnP](https://godbolt.org/z/5dG5M5EnP) |
| [#3377](https://github.com/microsoft/DirectXShaderCompiler/issues/3377) | Access violation (silent, no error messages generated) when trying to build pixel shader | complete | **repros** | always; **all 20** releases v1.4.1907→v1.9.2607, no invalid probes | keep open | [rqvfvYc93](https://godbolt.org/z/rqvfvYc93) |
| [#3693](https://github.com/microsoft/DirectXShaderCompiler/issues/3693) | Vector element index out-of-bounds not leading to compile error | partial | **repros** | always v1.6.2104→v1.9.2607 (18); v1.4.1907 and v1.5.2010 reject `lib_6_6` | keep open | [7KGrq6xMe](https://godbolt.org/z/7KGrq6xMe) |

Confidence is `high` on all five. **`text_stale` is set on #2922 only** — the body tells a
reader to open `PixTest.cpp` and change `-Od` to `-O1`, an edit that is already upstream, so
someone following the instructions finds nothing to change and a suite that passes 18/18.
#3092 and #3693 considered `text_stale` explicitly and rejected it in writing, #3092 citing the
#8737 failure mode by name.

**Compiler Explorer: four links, one deliberate skip.** All four were re-fetched during
collation via `GET /api/shortlinkinfo/<id>` and every one returns **HTTP 200** with the pane
set the draft claims (`End684Ycq`: three DXC panes; `5dG5M5EnP`: two DXC + Clang; `rqvfvYc93`:
FXC + two DXC; `7KGrq6xMe`: FXC + two DXC + Clang). #2923's skip is recorded with a reason and
is correct: CE runs `dxc` only, the PIX passes live in `dxcompiler.dll` behind `IDxcOptimizer`,
and `repro.hlsl` compiles cleanly on every release — a link would show a clean compile and
nothing about the defect.

Two links carry limits the drafts state:

- **#2922's link cannot show the fix**, for the same reason #2918's could not: the pass is
  unreachable from `dxc.exe` and from CE. The link exists to show the pointer-typed
  `dbg.value` that *triggers* the bug, against `-Od`'s `dbg.declare`.
- **#3693's link publishes `case-compute.hlsl`, not `repro.hlsl`** — a compute restating,
  because FXC has no raytracing profile at all. The substitution is recorded in
  `godbolt-source.txt` and stated in the draft.

Drafts were written by `claude-opus-4.6` (#2923, #3092, #3377, #3693) and one worker that could
not self-identify its model (#2922 — the same limitation batch 007 recorded). All five carry
`reviewed_by: gpt-5.6-sol`; #2922's field also records a separate blind reproducibility check
by the same model, run during the open phase.

**Consistency check between `notes.md`, `verdict.json` and the DB: two defects found, both in
compressed fields, neither verdict-affecting.** See
[Verdicts checked against their own evidence](#verdicts-checked-against-their-own-evidence).

## Per-issue findings

### #2922 — the fix is real, the attribution is inferred, and neither claim came from `dxc.exe`

`dxc.exe` cannot run `-dxil-dbg-value-to-dbg-declare`, and neither can a locally built
`opt.exe`, which does not link the PIX passes. `match.json` therefore tests only the
**precondition** — that `-O1` emits a pointer-typed `llvm.dbg.value` — which is why the
recorded `history` field opens with `DO NOT READ THE BISECT LINE AS SYMPTOM HISTORY`. It says
`regressed-in v1.6.2104` because that is when `dxc` first emitted the pointer form for this
shader, not because anything regressed. This is batch 007's method finding 2 recurring
verbatim; the worker recognised and documented it rather than being caught by it.

The real history is in `manual-case-release-history.txt`, produced by driving each release's own
`dxcompiler.dll` through `dxopt -external <release>/dxcompiler.dll -external-fn
DxcCreateInstance`. Counting the pass's own `llvm.dbg.declare` output at `-O1`:

| release | `llvm.dbg.declare` emitted |
| --- | --- |
| v1.6.2104, v1.6.2106, v1.6.2112 | **0** — variable dropped |
| v1.7.2207 … v1.9.2607, and `main` | 2 |

All 19 of those builds saw identical input. Two are excluded, and the second exclusion is the
interesting one:

- **v1.4.1907** rejects `as_6_5` — a loud invalid probe of the kind `bisect` already trims.
- **v1.5.2010 compiles the repro successfully, exits 0, and emits no `DILocalVariable` at
  all.** The pass has no input, so the probe measured nothing while looking entirely healthy.
  Only the per-release `-Od` control exposed it. This is a **quiet** invalid probe and the
  tooling cannot see it; it is now a documented rule in step 6.

The reporter's own repro passes 18/18 (`TE.exe ClangHLSLTests.dll /name:PixTest::PixStructAnnotation_*`),
but tests and fix landed together so that alone would be weak — which is exactly why the
pass-level measurement was done.

**Residual, out of scope and stated in the draft:** the pass still returns early when a
pointer-typed `dbg.value` is not an `AllocaInst` (`// We only know how to handle AllocaInsts for
now`). No shader was tested against that path.

### #2923 — the cross-probe answers *where* before it answers *when*

The 22-build hand-run matrix gives a clean transition at v1.6.2106. On its own that names a
window and nothing else. The **component cross-probe** — the 2×2 of {dxc 2104, dxc 2106} ×
{passes 2104, passes 2106} — is what converts it into a location: `dxc=2104/passes=2106`
reproduces, `dxc=2106/passes=2104` does not, so the behaviour follows the **pass DLL** and the
change is in `lib/DxilPIXPasses`, not in the debug info `dxc` emits. That is a stronger and
cheaper result than any amount of further bisection over `dxc` could have produced.

The IR shape is unchanged across the transition. The six `DW_OP_bit_piece` shadow allocas for
`main`'s `p` exist at v1.6.2104 too — but there each carries a `!pix-alloca-reg-write`, and from
v1.6.2106 those writes stop.

`git log v1.6.2104..v1.6.2106 -- lib/DxilPIXPasses/` holds **nine** commits, **five** of which
touch `DxilDbgValueToDbgDeclare.cpp` (re-derived at collation into
`manual-case-window-commits.txt`). Release-to-release probing cannot tell nine commits apart, so
**the draft names none**, per the orchestrator's explicit instruction. The bound is stated
instead.

**The caveat that constrains the whole verdict.** At v1.5.2003 — 2020-03-25, the release current
when the issue was filed on 2020-05-27 — `repro.hlsl` is numbered perfectly. v1.5.2003 is
`bisectable=0` in the catalog (it is a GitHub prerelease), so it was fetched and run by hand;
without that, the history would read "broken since before we can check" and would be wrong. The
repro is a reconstruction from the issue's own instruction and the issue says *"Not clear yet
what set of structs are affected"*, so it may not be the reporter's instance. It is the same
scenario, and it is broken today. The draft says all of this.

### #3092 — the request has narrowed, and one of the three blockers has landed

`[numthreads]` already accepts a *named* compile-time constant: `static const uint TGSIZE_X = 4;`
compiles and emits `OpExecutionMode %main LocalSize 4 1 1`. What it will not accept is a
specialization constant, because `[[vk::constant_id(1)]] static const uint` is rejected with
`error: specialization constant must be externally visible`. So the missing capability is a
dimension that is **not known at compile time**, not compile-time constants in `numthreads` —
a materially narrower ask than the 2020 title implies.

Since the maintainer's 2025-01 checklist, **item 3 has landed**: PR #7378 ("[SPIRV] Refactor
OpExecutionModeId", `e866b4bac`, merged 2025-04-29). `LocalSizeId` is now reachable from inline
SPIR-V — `vk::ext_execution_mode_id(38, TGSIZE_X, 1u, 1u)` with `-fspv-target-env=vulkan1.3`
compiles and emits both `OpExecutionMode ... LocalSize 1 1 1` and
`OpExecutionModeId ... LocalSizeId %TGSIZE_X %uint_1 %uint_1`. It is not a substitute:
`[numthreads]` remains mandatory on a compute entry point, so the module carries both execution
modes. It passes DXC's bundled validation; **no driver was tested**.

Items 1 and 2 remain open HLSL spec questions, and the compute-derivatives coupling is still in
the code (`addDerivativeGroupExecutionMode` picks the quad layout by reading back the already-
emitted `LocalSize` operands, `SpirvEmitter.cpp`). PRs #7084 (draft) and #7439 (`Fixes #3092`)
are both still open.

**A closed duplicate exists and nothing links the two.** #4128 "[SPIR-V] specialization
constants are not allowed in numthreads" was closed `NOT_PLANNED` on 2024-05-09. It is the same
request. Worth a maintainer's attention: one of the two is now closed and the other has an open
`Fixes` PR.

### #3377 — the crash is the least interesting thing about it

Still reproduces on `main` and on **all 20** release binaries, with no invalid probes anywhere
in the scan. The oldest predates the 2021-01 report by eighteen months, so `always-repro'd` here
means genuinely always.

**The Debug assert and the reported Release crash are the same failure.** Releases are Release
builds, where `DXASSERT` is `do { } while (0)` (`include/dxc/Support/Global.h:356`) — so a quiet
release binary is not evidence of a fix. Continuing past the traps under `cdb` (which then runs
what a release build runs) reaches `STATUS_HEAP_CORRUPTION` and dies in `memcpy` under
`DxilParameterAnnotation::AppendSemanticIndex` ← `AllocateSemanticIndex` ← `allocateSemanticIndex`
← `flattenArgument` — @Dwedit's 2021 stack, frame for frame, including "crashes in a memory copy".

**The minimization goes one step past @damyanp's.** No matrix, no `SamplerState`, no second
entry point, and `uniform` is not needed:

```hlsl
float4 main_fragment(Texture2D<float4> decal : TEXUNIT0) : SV_Target {
  return decal.Load(int3(0, 0, 0));
}
```

Both spellings fail: remove the `: TEXUNIT0` and DXC answers `error: Semantic must be defined
for all parameters of an entry function or patch constant function`.

**Two fixes were attempted and both lapsed** (`manual-case-linked-prs.txt`, generated at
collation from read-only `gh` GETs):

| PR | Opened | State | Closing rationale |
| --- | --- | --- | --- |
| #4538 "Add extra type null checking to prevent AV" | 2022-07-01 | **CLOSED, unmerged** 2024-03-28 | — |
| #4554 "param validation for uniform / resources in entry point functions" | 2022-07-13 | **CLOSED, unmerged** 2025-02-06 | *"Merge conflicts, and according to @Tex3D it seems like this is the wrong direction"* |

#4554's body names this issue directly: *"This was causing AV problems as described in #3377."*
So the direction that was tried was judged wrong and nothing replaced it — which changes the
suggested action from "confirmed broken" to "a person must decide what the right direction is".

**The output-matching trap, quantified.** Across 10 runs each on four builds, all 40 failed and
none produced DXIL or a source diagnostic. **8 of the 20 release captures have completely empty
stderr** (v1.4.1907, v1.5.2010, v1.7.2308, v1.8.2405, v1.8.2502, v1.8.2505, v1.8.2505.1,
v1.9.2602), and v1.8.2502 alternates run to run between a silent `0xC0000409`
(`STATUS_STACK_BUFFER_OVERRUN`) and a `0xC0000005` with a message — same binary, same input.
Any predicate keyed to message text would have drawn a fix boundary through the middle of an
issue that has never once worked.

FXC 10.1 compiles the body's shader as `ps_5_0` with exit 0, so the report's opening comparison
still holds.

### #3693 — the diagnostic exists; the front end just does not reach it

Hoisting the access out of the subscript makes the *same compiler* reject the *same expression*:
`error: vector element index '3' is out of bounds`. Left as the index operand of another
subscript, `g_vertices[indices[3]]` compiles clean, the element becomes `undef`, and it is used
as the buffer index — `@dx.op.rawBufferLoad.f32(i32 139, %dx.types.Handle %31, i32 undef, ...)`
— with validation passing.

Across **eleven** tested positions the front end diagnoses every one (local initializer, call
argument, assignment target, arithmetic operand, `.w` swizzle) except when the access is another
subscript's index. The hole is not vector-specific: `g_vertices[a[3]]` on a 3-element *array*
behaves identically while `uint x = a[3];` errors with `array index 3 is out of bounds`.

Source: `CheckHLSLArrayAccess` (`tools/clang/lib/Sema/SemaHLSL.cpp:16904`) recurses into
`getArg(0)` — the object being subscripted — and never into `getArg(1)`, the index.

**Cross-compiler, with the control that makes it mean something.** FXC rejects it (`error X3504:
array index out of bounds`) in both positions. **clang-dxc trunk accepts both** — no diagnostic
even for the hoisted form DXC catches — and the index becomes `poison`. The control is a
`indices.w` spelling of the same out-of-bounds element, which Clang *does* reject
(`vector component access exceeds type 'const uint3'`), proving Clang is looking and this is a
real gap in the new front end rather than the flags being ignored.

**A trap worth stating for anyone spot-checking the attachment:** `DefaultRT.zip` uses
`RootFlags(XBOX_RAYTRACING)`, which public dxc rejects in the root-signature parser — an error
that reads perfectly well as "the compiler diagnoses this now" if that is what you are looking
for. Replacing the token with `0` compiles the file unchanged otherwise.

## Verdicts checked against their own evidence

Every verdict was re-derived from `expected.md`, `notes.md`, `match.json`, `verdict.json`,
`comment.md` and the captured output files. **All five follow from the evidence on disk. No
verdict was overturned.** Two defects were found, both in the compressed fields
`SKILL.md` warns are read first and reviewed least, and neither changed a conclusion:

| Field | Said | Evidence says | Fix applied |
| --- | --- | --- | --- |
| #2922 `summary` | "Fixed … **by** `c0676c7ca`" | `notes.md`: "strong, not certain"; 248-commit window, commit never built | "the evidence points to `c0676c7ca`"; window described as "strong but window-bounded **and not proven**" |
| #3693 `summary` | "**FXC rejects the same source** with X3504" | FXC has no raytracing profile. `godbolt-source.txt` and every FXC capture name `case-compute.hlsl` — a compute *restating* | "FXC has no raytracing profile, so the cross-compiler comparison used a compute restating of the same construct; FXC rejects that with X3504" |

Both long-form drafts were already correct — #2922's body says "strong rather than proven" and
#3693's says "restated as a compute shader so FXC can compile it". That is the shape of this
failure: it survives *because* the long form is right, so nobody re-reads the one-liner.

Two further wording corrections were applied for scope, not error: #3377's summary now says "in
everything tested the trigger is…" and #3092's says "all 19 catalog releases with SPIR-V
CodeGen" rather than "all 19 SPIR-V-capable releases".

**One factual error in `notes.md`, corrected in place with a marked parenthetical.** #2923's §4
lists `650de80d3` (#3855) among the commits in the regression window. It is not in the window;
its release-branch cherry-pick **`dad1cfc30`** (#3855)(#3856) is — the same change with a
different SHA. The section is explicitly labelled "a list of candidates, not a finding" and no
draft named a commit, so nothing downstream was affected. The list was also incomplete (six of
nine); it is now re-derived by a committed script.

**Provenance and the single-writer rule.** `git status` on `scripts/` was clean at the start of
collation and `SKILL.md` carried only the orchestrator's own open-phase addition, so no worker
wrote outside its issue directory. Ground truth was verified by tree, as above.

## Cross-issue analysis

### #2918, #2922 and #2923 are the same *area*. They are not the same defect.

All three were filed **on 2020-05-27, within ten minutes of each other**, by @jeffnn, all
unlabelled, all carrying the same never-answered @damyanp question from 2024-06-27:

| # | Filed | Verdict | Direction |
| --- | --- | --- | --- |
| 2918 (batch 007) | 21:23:53Z | does-not-repro | **fixed** in v1.6.2104 |
| 2922 | 21:29:23Z | does-not-repro | **fixed** between v1.6.2112 and v1.7.2207 |
| 2923 | 21:33:00Z | repros | **regressed** at v1.6.2106 |

**They resolve in three different directions, and that is decisive.** #2918 was already fixed
before #2923 broke; #2923 broke before #2922 was fixed. A single root cause cannot produce that
ordering. Two of the three (#2918, #2922) implicate `DxilDbgValueToDbgDeclare.cpp` directly, and
#2923's cross-probe localises to the same directory with five of the nine window commits
touching that same file — so they are **adjacent in code**, which is exactly why "same area" is
defensible and "same defect" is not.

**A maintainer already answered this question, in public, and the answer survives.** In review
on PR **#3746** ("PIX: Change insertion point to after referenced value", `320d40bf3`, merged
2021-05-05 — a commit that sits *inside* #2923's regression window), someone asked *"Do you think
this might fix #2922?"* and @jeffnn replied:

> *"I don't think so- that bug is all about not even handling the pointer properly."*

That is the author of all three issues separating two of them, on the merits, in the window where
they overlap. **No duplicate relationship is claimed and none should be.** `duplicate-of` still
has zero rows across 40 triaged issues.

**#2918's harness does not apply to #2922 or #2923, and this was confirmed rather than assumed.**
Each issue's symptom needed its own harness: #2918 has `run-pix-passes.py`, #2922 wrote
`measure.py`, #2923 wrote `run-2923.cmd` + `check-2923.py`. They encode three different symptoms
over the same pass pipeline. The orchestrator explicitly asked that this not be assumed; it was
checked.

### No other issue in this batch shares a root cause, and none subsumes another

#3092 (a SPIR-V capability that has never existed), #3377 (an SROA semantic-index AV) and #3693
(a missing front-end bounds check) are unrelated to each other and to the PIX pair. The only
weak adjacency is that **#3377 and #3693 are both "the compiler does not say anything"** — but
one is a crash with no diagnostic and the other is a clean compile with no diagnostic, which are
opposite problems: #3377 needs a diagnostic *instead of* a crash, #3693 needs a diagnostic
*instead of* silence. Both drafts propose `diagnostic`-adjacent labels for that reason and
neither claims a link.

### A closed duplicate nobody linked

**#4128** "[SPIR-V] specialization constants are not allowed in numthreads" was closed
`NOT_PLANNED` on 2024-05-09. It asks for exactly what #3092 asks for. #3092 is open and has an
open `Fixes #3092` PR (#7439). This is not a triage verdict — nothing was measured about #4128 —
but it is a backlog-hygiene finding a maintainer can act on in one click.

### Two workers independently discovered the same tooling trap

This is the strongest signal collation can produce, because the workers could not have copied
each other:

1. **`godbolt` reports only each pane's FIRST line.** Hit by **#3092** (whose
   `hlsl_clang_trunk` first line is a `-Qembed_debug` unused-argument warning — the actual
   finding, Clang rejecting the shader with DXC's first diagnostic word for word, is further
   down) and independently by **#3377** (first line enough to see `SIGSEGV`, not enough to count
   Clang's thirteen errors or
   confirm FXC succeeded). **Both wrote their own `ce-probe.py` POSTing to
   `/api/compiler/<id>/compile`.** Six files by that exact name now exist across the corpus
   (#2331, #2528, #2530, #3092, #3377, #3693) alongside six more CE clients under other names.
   Two people paying the same cost in one batch is a tool defect, not a habit — fixed, see
   below.
2. **Short-link read-back verification** via `GET /api/shortlinkinfo/<id>` was independently
   adopted by **#3377, #3693 and #2922** — three workers, two of them writing it up as a
   proposal in `method-notes.md` and the third simply doing it and committing the result in
   `manual-case-godbolt-panes.txt`. Also fixed.

### The timeline check, run across all six issues

Carried-over item 4, executed. Cross-referenced events per issue: **2922: 1, 2923: 0, 3092: 3,
3377: 3, 3693: 0, 2918: 0.** Every one predates this batch and is a legitimate upstream
reference. **No cross-reference was created by this triage branch.** The read-only rule held.

### Patterns across the five verdicts

- **Four of five reproduce; the fifth was fixed in 2022 and never closed.** Same ratio as batch
  007, and the same property of the sample rather than of the backlog.
- **Two of five have a symptom `dxc.exe` structurally cannot show.** Both PIX issues needed
  `dxopt -external` against release DLLs. That is the second consecutive batch in which the
  headline result came from outside the compiler driver.
- **Three of five are about the compiler not saying something** (#3377 crash with no message,
  #3693 missing bounds error, #3092 a diagnostic that is *correct* but marks a missing feature).
  Absence-shaped symptoms are where the predicate system is weakest, and both of this batch's
  predicate lessons came from them.
- **Two of five needed a release the catalog does not bisect** (#2923's v1.5.2003) or a release
  that lies about being a valid probe (#2922's v1.5.2010).

## Proposed label changes

None applied. All are proposals recorded in `verdict.json`.

| # | Current | Proposed additions | Warrant |
| --- | --- | --- | --- |
| #2922 | *(none)* | `PIX`, `bug`, `debug info` | The issue carries no labels at all. All three fit the original report, and they remain worth applying even on close, so the fixed defect is findable. |
| #2923 | *(none)* | `PIX`, `bug`, `debug info` | Same three; here the cross-probe positively locates the defect in `lib/DxilPIXPasses` and the release scan shows a regression point. |
| #3092 | `spirv` | `enhancement`, `hlsl-next` | Keep `spirv`. The remaining blocker is a language spec decision, not an implementation defect — which is what `enhancement-not-bug` records. |
| #3377 | `bug`, `crash`, `incorrect-code` | `diagnostic`, `fxc-disagrees` | All three current labels still fit. `diagnostic` because the resolution both @tex3d and @damyanp point at is to *reject* this rather than crash on it; `fxc-disagrees` for the measured FXC/DXC difference. |
| #3693 | `bug`, `diagnostic` | `fxc-disagrees`, `incorrect-code` | `fxc-disagrees` is measured (FXC X3504 vs DXC silence). `incorrect-code` because the silent `undef` reaches a resource index and passes validation. |

No removals are proposed on any issue in this batch.

## Carried-over tooling work

Batch 007 recorded four items and did not do them; the batch-008 orchestrator notes added a
fifth. **Three are now implemented with tests, one is superseded, one is deliberately not
done.** `python scripts/test_predicates.py` passes.

### Done

**3. `shlex.split` eats Windows backslashes — fixed.** `split_cmd()` now runs `shlex` in POSIX
mode with `escape = ""`, so `-I inc\sub` and `-Fo C:\out\a.dxo` survive while quoting still
groups `"my repro.hlsl"`. Both call sites (`execute` and `ce_args`) use it. **First, the impact
question batch 007 asked and did not answer: no committed `cmd.txt` anywhere in the corpus
contains a backslash, so no verdict was affected.** This removes a trap before it is stepped on.
Four new tests.

**4. Timeline check — performed and promoted.** Run across all six related issues (results
above) and written into `SKILL.md`'s batch-report section as a standard step, with the command
and the batch-008 result as evidence.

**5. The worker-brief `audit` defect — fixed.** `SKILL.md` told briefs to forbid `audit --issue`
alongside `reindex`. `audit` opens no transaction and writes no table; it exists *because*
`reindex` was the only route to the completeness check and cost two batch-004 workers their
rows. The brief now forbids `reindex` only and positively encourages `audit --issue <n>` as a
pre-report self-check.

**Bonus, from the cross-issue analysis — two tool defects with two independent witnesses each:**

- `godbolt` now writes the **full text of every pane** to `manual-case-godbolt-verify.txt`
  instead of throwing everything past line 1 away. The data was already in hand; only the
  printing discarded it. This is what #3092 and #3377 each wrote a client to work around.
- `godbolt` now **reads the short link back** via `GET /api/shortlinkinfo/<id>` and warns if the
  stored pane list or source differs from what was sent. Verified against the live API on all
  four of this batch's links.

**Also fixed, from #2923's method notes:** `triage.py run` silently defaulted to
`--compiler main-debug`. For an issue registered against a harness compiler that produced a
plausible-looking `no-repro` and a DB row contradicting two existing `repro` rows, with nothing
in the output saying which compiler had been chosen. `run` now infers the compiler from the
issue's existing non-release captures when `--compiler` is omitted, and says so on stderr.
Three new tests.

### Not done, with reasons

**1. The `script` predicate kind — superseded, not implemented.** #2923 found a strictly better
answer to the same problem: register the harness *as a compiler*
(`triage.py compiler --id main-debug-pix --exe <abs path>/run-passes.cmd`). The wrapper needs an
absolute path, must answer `--version`, and should take the real compiler from an environment
variable. After that `run`, `--expect`, variants, `audit` and — crucially — `reindex` all work
unchanged, which is the exact gap the new predicate kind was meant to close. It requires no new
predicate machinery and no new code path that could disagree with `classify`. `bisect` still
cannot drive such a repro, because it builds its own command line from `cmd.txt`; that is the
one remaining limitation and it is now documented. **Recommendation: close item 1.**

**2. The predicate `role` marker — assessed, not implemented.** `--expect match` /
`--expect no-match` / `--expect invalid-probe` is recorded per capture, re-checked on every
`reindex`, and already distinguishes a control that should match from one that should not. The
marker's remaining value is narrower than batch 007 assumed: it would let `bisect` refuse to
report a transition derived from a *precondition* predicate, which is #2922's `regressed-in
v1.6.2104` line. That is real but it is a `bisect` change, not a predicate change, and doing it
under time pressure at the end of a batch is how tooling gets destabilised. **Left open,
re-scoped: the useful half is "let a predicate declare that it asserts a precondition, and make
`bisect` refuse to narrate a history from it".**

## What batch 008 taught us about the method

Every `method-notes.md` was read in full (102, 176, 78, 107 and 101 lines). What follows is what
survived the filter; issue-specific noise was rejected. All of it is now in `SKILL.md`.

### 1. An absence predicate can be *falsified* for free — the documented hazard runs the other way

`SKILL.md` has warned since batch 001 that an absence predicate is *satisfied* for free by a
compile that never started. **#3092 found the mirror image, and it is harder to see because a
clean result reads as good news.** Its predicate was `not_regex "LocalSizeId"`. DXC's SPIR-V
validator **echoes the instruction it is rejecting into the diagnostic**, so a *failed* compile
printed `LocalSizeId` and the probe scored "no match" — reporting the capability present on the
strength of the error message saying it is absent.

**Tightening the regex does not help.** The validator prints the instruction verbatim, so any
pattern matching the good output also matches the complaint. The only thing that caught it was
`--expect match` on a control nobody would have thought to doubt. Generalised rule, now in step
4: when the symptom is the absence of a token, check whether the compiler's own diagnostics
quote that token — validators, verifiers and `-verify` modes routinely do.

### 2. A control cannot catch a broken reader

**#2923's most valuable finding, and it is a limit on the control discipline itself.** Controls
prove a predicate discriminates between two inputs. They cannot prove that the thing *producing*
the text under test is working, because a broken reader reports both arms clean and the pair
looks consistent.

The harness scraped PIX register numbers out of LLVM IR with `\S+` standing in for a type name.
`\S+` cannot match `[1 x float]*` — LLVM's type printer puts spaces inside types. The
reproducing case scored clean; so did the control; they agreed.

The fix is not a better regex. It is a **self-consistency line**: a harness that generates the
text its own predicate scores must assert what it expects to find and fail loudly when it finds
nothing (`PIX-2923: PARSE-WARNING: 0 variables parsed`). Any harness that can return "nothing
here" and "nothing matched" through the same channel will eventually be believed.

### 3. `godbolt` reported only the first line, and it hid the finding twice in one batch

Covered above. The point worth carrying forward is methodological, not technical: **when reading
`method-notes.md` at collation, sort observations by how many workers independently reported
them.** One worker noticing something is a data point; two workers who never spoke paying the
same cost is a defect with a location.

### 4. `godbolt-note.txt` is compiled, not merely displayed

**#2922.** The banner is prepended to the source CE actually builds, and DXC records its input
in `!dx.source.contents` — so literal IR quoted in a "what to look for" note appears verbatim in
that pane's own DXIL output, where it satisfies any text search a reader (or a future predicate)
runs against the pane. Describe the instruction in prose, or quote it in a form that cannot be
confused with the compiler's own output.

### 5. `run` silently chose a compiler, and the wrong answer looked right

**#2923.** Covered under carried-over work. The general shape is worth naming: *a default that
is right for most cases is exactly the kind that is not noticed when it is wrong.* The output
said `no-repro` and named no compiler; nothing was visibly missing.

### 6. `--repeat` is for a nondeterministic *occurrence*, not a nondeterministic *form*

**#3377.** These look similar and want opposite treatment. #3377's crash varies in shape run to
run (v1.8.2502 alternating between a silent `0xC0000409` and a messaged `0xC0000005`, same
binary, same input) but it crashes every time, and *no probe anywhere in the 20-release scan
scored clean*. With no clean result there is no boundary that could be an artefact, so
`--repeat` had nothing to protect. The right measurement for varying form is a hit-rate count on
a few builds (40/40 here), quoted as counts; the right measurement for varying occurrence is
`--repeat` across the scan.

### 7. Run the feature-presence control on *every probed release*, not only on ground truth

**#2922.** v1.5.2010 compiles the repro successfully, exits 0, and emits no `DILocalVariable` at
all — so the debug metadata the whole issue is about is simply absent and the probe measured
nothing while scoring a confident `no-repro`. Nothing in the exit status or the diagnostics says
so. This is a **quiet** invalid probe; `bisect` trims the loud kind and reports the count, and
can do nothing about this one.

### 8. The bisectable catalog has a fourteen-month hole, and it is where 2020 issues live

**#2923.** `v1.5.2003` is `bisectable=0` (a GitHub prerelease), so the scan jumps v1.4.1907
(2019-07) straight to v1.5.2010 (2020-10). Any issue filed in that window must probe v1.5.2003
by hand. Here it was decisive in the least convenient direction — the repro is numbered
*correctly* at the exact release current when the issue was filed, which is the difference
between "still broken since 2020" and "this reconstruction may not be the reporter's instance".

Related, from **#3092**: the effective SPIR-V floor is **v1.5.2010**, which postdates that
issue's 2020-08-19 report, so no probeable release covers the reporter's own build.

### 9. A missing-diagnostic issue has a standard control pair, and it needs both

**#3693.** The symptom is silence, and silence has two innocent explanations: the compiler never
looks, or there was nothing to say. So run (a) an input the compiler *does* diagnose, and (b) an
input that is simply correct code. **The predicate must carry a positive anchor or (b) is
meaningless** — a bare absence clause is satisfied by correct code too, so without an anchor the
second control cannot fail.

### 10. When the symptom is in a pass `dxc.exe` cannot run, register the harness as a compiler

**#2923**, superseding batch 007's proposed `script` predicate kind. Also the `dxopt -external`
recipe and its load-bearing argument order (`-o=`, `-external`, `-external-fn` must all precede
the input file; wrong order gives a bare `0x80070057`), and the **component cross-probe** that
answers *where* before *when*. All now in step 3.

### 11. Count a commit window by *file*, and remember cherry-picks have two SHAs

**#2923, found at collation.** The orchestrator's notes said three of nine window commits touch
the relevant pass, reading commit titles. `git log <a>..<b> -- <the file>` says **five**. Titles
are unreliable in both directions; ask git which commits touched the file.

Separately, `650de80d3` and `dad1cfc30` are the same change — mainline and release-branch pick —
and only the pick is in the window. `git merge-base --is-ancestor <sha> <tag>` before naming a
SHA.

### 12. Generate every `manual-case-*.txt` from a script that echoes the command

**#2922.** A transcribed command line is an assertion about what happened and is checked by
nobody; a committed #2922 capture opens with a `$ git tag --contains … | sort -V` line that was
not the command actually run. `subprocess.list2cmdline(argv)` prints exactly what was executed.
This collation followed its own advice: both new captures
(`2923/manual-case-window-commits.txt`, `3377/manual-case-linked-prs.txt`) ship with the
generator that produced them.

### 13. Smaller measured items, all promoted

- **`cdb` from PowerShell silently produces nothing** — no error, exit 0, which reads as "the
  debugger found nothing". Go through `cmd.exe` with the redirection inside and no `--`
  separator. And **a `.cmd` harness cannot reliably report `ERRORLEVEL`**: `set /a` resets it and
  a nested `for /f` clobbers it. Capture exit statuses from Python. (#3377)
- **CE returns ANSI SGR escapes** in compiler output — strip them in the *matcher*, never in the
  committed capture, because hand-editing a capture is falsification. (#3377)
- **`run --args` is a full argv, not extra flags** — it must repeat the source filename even when
  `--shader` also names it. (#3693)
- **`audit` wants a tool-made capture for every `.hlsl` in the directory**, so a script-driven
  matrix needs one representative `run` per source file. (#3693)
- **An attachment from a real project carries platform tokens** — `RootFlags(XBOX_RAYTRACING)`
  makes stock dxc fail in the root-signature parser, readable as "the compiler diagnoses it now".
  Grep attachments for vendor tokens before running them. (#3693)
- **Never point a release-sweep script at the same output filenames as the ground-truth run** —
  #2923's sweep silently overwrote ground-truth `.ll` artifacts. Name provenance into the
  filename. (#2923)
- **`triage.py sql`: the compilers table column is `exe_path`, not `exe`.** (#3377)

### 14. `triaged_with_commit` stores a SHA that a history rewrite kills

**#3693 proposed it and this batch proved it.** `triaged_with_commit: ab5400907` points at a
commit that no longer exists. The tree hash does not change under a message rewrite —
`574a2bd25…` is identical across both SHAs — so storing it alongside would make the provenance
record self-verifying instead of requiring a note in a handover document. **Not implemented**
(it is a schema change and every existing row would need backfilling); recorded as a proposal.

### 15. The compressed fields need their own review pass, and this batch is the evidence

`SKILL.md` already carries the #8737 lesson: *compression must only remove claims, never add
one*, and *step 10 reviews `comment.md`; nothing reviews `summary` or `text_stale`*. What batch
008 adds is that **collation must therefore read them as a deliberate separate pass** — not
"check the verdicts", but re-read every `summary` and `text_stale` against that issue's
`notes.md` sentence by sentence. Two of five had unsupported compressions above correct
long-form drafts. That is now a documented collation step.

## What the step-10 review changed

`gpt-5.6-sol`, briefed exactly as step 10 describes (concision primary, subtraction only, no new
sections, technical evidence off-limits, quoted current text plus exact replacement demanded,
plus a mandatory factual/arithmetic section). It returned a long structured report — roughly
thirty numbered suggestions across the five drafts plus a separate arithmetic section.
**Applied with judgement, not wholesale.**

> The review itself was a sub-agent exchange and **is not committed to disk**, so the counts in
> this section are reported from the collation transcript rather than from a file. What *is*
> verifiable is the outcome: the five `comment.md` drafts and the two capture files the review
> prompted. Future batches should consider writing the reviewer's report to
> `data/reports/batch-NNN-step10.md` so this section is checkable.

**Cross-issue claims were settled *before* the review**, per step 10's own instruction — #3377's
lapsed-PR section and #2923's commit-window bound were added first, so the reviewer saw the
drafts a maintainer would.

### Accepted (about two-thirds)

- **Overclaim in #2922's opening.** "fixed … **by** `c0676c7ca`" → "the evidence points to
  `c0676c7ca`". Correct, and it made the opening consistent with the draft's own later "strong
  rather than proven". The same correction was then applied to the `summary`.
- **"There is no spelling of this that compiles"** (#3377) → "Both spellings fail". Only the
  with-semantic and without-semantic forms were tested; the original generalised past them.
- **"No diagnostic is ever produced"** (#3377) → scoped to the 40 measured runs and 20 release
  captures. (This sentence had already been corrected once during collation, from "The failure
  is silent far more often than not", which the evidence also did not support. It took two
  passes to get right.)
- **"every SPIR-V-capable release" / "v1.4.1907, the only older one"** (#3092) → "all 19 catalog
  releases with SPIR-V CodeGen". A genuine arithmetic catch: v1.5.2003 exists and was not probed
  for this issue.
- **"So no declaration satisfies both today"** (#3092) — dropped; only the ordinary and `static`
  forms were tested.
- **"so it really does need an answer before a spec-constant dimension can work"** (#3092) —
  dropped as speculative necessity, keeping the measured `addDerivativeGroupExecutionMode` fact.
- **"looks like a language/product call rather than a purely mechanical fix"** (#3693) → "is a
  language/product call". "Purely mechanical" is an effort claim.
- Assorted rhetorical framing: "The interesting part is that…", "Left where you wrote it…",
  "One caveat, out of scope for this issue…", "Worth stating because…". A comment landing on a
  stranger's five-year-old issue should read as a report.

### Rejected, and why

- **Cutting #3377's lapsed-PR section to bare PR numbers.** The reviewer marked it LOW
  confidence because the PR metadata "is not recorded in `issue.json`, `notes.md`, or
  `verdict.json`" — which is true, and is a *briefing* limitation, not a defect in the claim.
  **The right response was to capture the evidence, not delete the finding.** Collation
  generated `3377/manual-case-linked-prs.txt` from read-only `gh` GETs, including the closing
  quotation verbatim. Same for #2923's commit counts →
  `2923/manual-case-window-commits.txt`. This is the documented "it flags anything absent from
  its brief as unsupported" failure mode, and it is worth treating as a prompt to strengthen the
  evidence rather than as a verdict.
- **Removing the one-line label rationales** (#2923, #3092, #3377). Step 9 asks for the label
  suggestion *and its one-line justification*; the reviewer does not know the house style. The
  lines were tightened instead.
- **Removing the direct answers to @damyanp's standing 2024 questions** (#2922, #2923). Those
  questions are unanswered on the real issues; answering them is a large part of what makes the
  comment worth posting. Shortened, not deleted.
- **"@damyanp's 2024 reading is right, and it goes one step further"** (#3377), called
  point-scoring. It is attribution — @damyanp did the first minimization, and dropping the
  credit would be worse than the wordiness. Reworded to "holds, and reduces further".
- **Rewriting #3693's eleven-position paragraph.** The original is accurate and the proposed
  replacement was not clearly better; only the front-end/validator distinction was worth taking.
- **Deleting "Possibly worth an issue there"** (#3693, on the Clang gap). Where the next step is
  a decision for another project, saying so is the point of the comment.

### Corrected in the other direction

Per `SKILL.md`'s "it can introduce an error while removing one", every accepted rewrite was
re-read against the evidence. One was pulled back: #2922's *"the fix is observably executing,
not merely present"* was rewritten by the reviewer to *"matching the `B.CreateLoad(V)` added by
the commit"*, which loses the discriminating fact. The final text keeps the contrast and drops
the flourish: *"Main's output contains … and v1.6.2112's does not, so the fix is executing
rather than merely present."*

### Arithmetic

The arithmetic section was the review's most valuable output, exactly as `SKILL.md` predicts:
almost every query in it was right, and two produced corrections that survived into the final
drafts (#3092's release count, #3377's release-window restatement). The one that was wrong —
that #2923's commit counts were unsupported — was right about the *files* and wrong about the
*claim*, and is what prompted the new capture.

## Proposed issue comments

These are **drafts for review, not posted**. No comment, label or state change
has been made on any issue. Each is written to be postable as-is by a maintainer, and every
claim in them is backed by captured evidence in `issues/<nnnn>/`.

They deliberately avoid promising fixes or timelines, and where the next step is a product or
language decision they say so rather than pre-empting it. Quoted compiler output was
re-verified before being written down.

Each draft ends with a trailer disclosing that it came from an assisted triage pass.

Source of each is `issues/<nnnn>/comment.md` — edit there, then re-run
`scripts/render_comments.py <batch>` to refresh this section.


### Draft — [#2922](https://github.com/microsoft/DirectXShaderCompiler/issues/2922)  value-to-declare pass not handling pointer case under -O1

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2922](https://github.com/microsoft/DirectXShaderCompiler/issues/2922).

**This no longer reproduces.** It was fixed between **v1.6.2112 and v1.7.2207**; the evidence
points to
[c0676c7ca](https://github.com/microsoft/DirectXShaderCompiler/commit/c0676c7ca1033a0e5c7a0b19caac6c42889b5b27)
("Handling dbg.value pointer case in O1.", #4375, Apr 2022). Verified on `main` @ `ab5400907`.

@damyanp — no, this does not need tracking.

The repro as written can't be followed any more: `PixStructAnnotation_*` already runs at both
levels unconditionally, via

```c++
static const OptimizationChoice OptimizationChoices[] = {
    {L"-Od", false},
    {L"-O1", true},
};
```

and the same commit deleted all three of

```c++
break; // don't run -O1 test until pointer types are dealt with by value-to-declare pass
```

(those opt-outs were added in Dec 2020, after this was filed). Running the tests as filed:

```
$ TE.exe ClangHLSLTests.dll /name:PixTest::PixStructAnnotation_*
Summary: Total=18, Passed=18, Failed=0, Blocked=0, Not Run=0, Skipped=0
```

Because tests and fix landed together, I also ran each release's *own*
`-dxil-dbg-value-to-dbg-declare` over `PixStructAnnotation_FloatN`'s shader, via
`dxopt -external <that release>/dxcompiler.dll`. Counting `llvm.dbg.declare` instructions the
pass emits at `-O1` (what `PixTest` walks to build `AllocaWrites`):

| release | `llvm.dbg.declare` emitted |
| --- | --- |
| v1.6.2104, v1.6.2106, v1.6.2112 | **0** — variable dropped |
| v1.7.2207 … v1.9.2607, and `main` | 2 |

All 19 of those builds saw the same input: `call void @llvm.dbg.value(metadata
%struct.smallPayload.0* %p1, ...)` — the pointer case. v1.4.1907 (no `as_6_5`) and v1.5.2010
(emits no `DILocalVariable` at all) can't reach the pass, so they're not evidence either way.

Main's output contains `%4 = load %struct.smallPayload.0, %struct.smallPayload.0* %p1` — the
`B.CreateLoad(V)` that commit added — and v1.6.2112's does not, so the fix is executing rather
than merely present. The v1.6.2112 → v1.7.2207 window holds 248 commits, three of them touching
`DxilDbgValueToDbgDeclare.cpp`, so the attribution is strong rather than proven.

[Compiler Explorer](https://godbolt.org/z/End684Ycq) — DXC 1.6.2112 `-O1`, trunk `-O1`, trunk
`-Od`. CE cannot run the PIX pass, so the link shows only the pointer-typed `dbg.value` that
triggers it, against `-Od`'s `dbg.declare`.

**Suggested action: close as fixed.** Suggested labels: `PIX`, `bug`, `debug info` (the issue
currently has none).

The pass still returns early when a pointer-typed `dbg.value` is not an `AllocaInst`
(`// We only know how to handle AllocaInsts for now`). I did not test whether any shader
reaches that path.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#2923](https://github.com/microsoft/DirectXShaderCompiler/issues/2923) Structs passed to subroutines (can) cause the numbering pass to get confused about offsets of members 

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2923](https://github.com/microsoft/DirectXShaderCompiler/issues/2923).

@damyanp — yes, **this still misbehaves on `main`** (`1.9.0.5433`, `ab5400907`).

No modified unit test is needed: `repro.hlsl` is
`PixStructAnnotation_SequentialFloatN`'s shader with the edit the issue asks
for:

```hlsl
struct smallPayload { float3 color; float3 dir; };
void Sub(smallPayload p) { DispatchMesh(1, 1, 1, p); }
[numthreads(1, 1, 1)] void main() {
  smallPayload p;
  p.color = float3(1, 2, 3);
  p.dir = float3(4, 5, 6);
  Sub(p);
}
```

```
dxc   -T as_6_5 -E main -Od -HV 2018 -enable-16bit-types -Zi -Qembed_debug repro.hlsl -Forepro.dxo
dxa   -extractpart=dbgmodule -o=repro.ildb.bc repro.dxo
dxopt -o=repro.bc repro.ildb.bc -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
opt   -S -o=repro.ll repro.bc
```

In the resulting module, `main`'s own local `p` (`DW_TAG_auto_variable`, source
line 19) is described member-by-member by PIX virtual registers 0..5 — and none
of them is ever written. All six member writes were numbered onto registers
6..11, which belong to the inlined subroutine's parameter copy
(`DW_TAG_arg_variable`, source line 16):

```
%0..%5   [1 x float]              regs[0]..regs[5]
         declares: p [DW_TAG_auto_variable src-line 19] !DIExpression(DW_OP_bit_piece, 0|32|64|96|128|160, 32)
         writes  -> registers: (none)

%6       %struct.smallPayload.0   !pix-alloca-reg !{i32 1, i32 6, i32 6}
         declares: p [DW_TAG_arg_variable src-line 16] !DIExpression()
         writes  -> registers: 6,7,8,9,10,11
```

`ValidateAllocaWrite` computes `regBase + index`, so the modified test fails
with `0 != 6` for `color.x` (and 1..5 likewise). The same happens at `-O1`:
there `main`'s `p` holds registers 6..11 and the callee's copy holds 0..5, but
it is again the **caller's** variable that receives no writes.

Two controls, same pipeline: the unmodified test shader is numbered correctly
(one variable, registers 0..5, all written), and so is the same repro with the
subroutine taking the payload **`inout`**. Here the by-value struct copy is the
trigger, not the subroutine call.

**What has changed since 2020.** Running each release's own `dxc.exe` and its
own `dxcompiler.dll` (via `dxopt -external`) over 22 builds:

| | v1.5.2003 … v1.6.2104 | v1.6.2106 … v1.9.2607, main |
| --- | --- | --- |
| `repro.hlsl` | numbered correctly | caller's `p` unwritten |

The IR shape is the same on both sides of that line — the same six
`DW_OP_bit_piece` shadow allocas for `main`'s `p`. At v1.6.2104 they each carry
a write:

```
  %1     [1 x float]   regs[0]  declares: p [DW_TAG_auto_variable src-line 19]
         writes  -> registers: 0            <-- v1.6.2104
         writes  -> registers: (none)       <-- v1.6.2106 onwards
```

Cross-probing {dxc 2104, dxc 2106} × {passes 2104, passes 2106} shows the
result follows the **pass DLL**, not the compiler, so the change is in
`lib/DxilPIXPasses` rather than in the debug info `dxc` emits. Nine commits
touch that directory in the window, five of them `DxilDbgValueToDbgDeclare.cpp`
(`git log v1.6.2104..v1.6.2106 -- lib/DxilPIXPasses/`); release-to-release
probing cannot tell them apart, so no commit is named here.

Caveat: at v1.5.2003 (2020-03-25), the release current when this was filed,
`repro.hlsl` is numbered perfectly. Since the issue says *"Not clear yet what
set of structs are affected"*, this repro is a reconstruction from the described
edit and may not be the instance seen in 2020 — but it is the same scenario, and
it is broken today.

No Compiler Explorer link: CE runs `dxc` only, and this shader compiles cleanly
there — the symptom is entirely in metadata the PIX passes add afterwards.

Suggested labels: `PIX`, `debug info` (the bad metadata is derived from
`llvm.dbg.value` by `DxilDbgValueToDbgDeclare`), and `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3092](https://github.com/microsoft/DirectXShaderCompiler/issues/3092) [SPIR-V] Allow thread group size to be specified with specialization constants

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3092](https://github.com/microsoft/DirectXShaderCompiler/issues/3092).

**Still absent.** Tested on `main` (`1.9.0.5433`, ab5400907) and on all 19 SPIR-V-capable
releases in the catalog from v1.5.2010 (2020-10) to v1.9.2607 — every one rejects it with the
same error. v1.4.1907, the only older one probed, answers `SPIR-V CodeGen not available` and is
not a valid probe.

Using the syntax @s-perron [proposed in 2023](https://github.com/microsoft/DirectXShaderCompiler/issues/3092#issuecomment-1792858686):

```hlsl
[[vk::constant_id(1)]] const uint TGSIZE_X = 4;
RWStructuredBuffer<uint> Out;

[numthreads(TGSIZE_X, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID) { Out[tid.x] = tid.x; }
```

```
repro.hlsl:14:2: error: 'numthreads' attribute requires an integer constant
[numthreads(TGSIZE_X, 1, 1)]
 ^          ~~~~~~~~
repro.hlsl:14:2: warning: Group size of 0 (0 * 1 * 1) is outside of valid range [1..1024] - attribute will be ignored [-Wignored-attributes]
[numthreads(TGSIZE_X, 1, 1)]
 ^~~~~~~~~~~~~~~~~~~~~~~~~~
repro.hlsl:15:6: error: compute entry point must have a valid numthreads attribute
void main(uint3 tid : SV_DispatchThreadID) {
     ^
```

[Compiler Explorer](https://godbolt.org/z/5dG5M5EnP) — dxc 1.6.2112, dxc trunk, and Clang.

**Two measurements narrow the ask.** `[numthreads]` already accepts a *named* compile-time
constant: the same shader with `static const uint TGSIZE_X = 4;` compiles and emits
`OpExecutionMode %main LocalSize 4 1 1`. But `[[vk::constant_id(1)]] static const uint` gives
`error: specialization constant must be externally visible`. What is missing is not
compile-time constants in `numthreads` but a dimension that is *not* known at compile time.

**Clang trunk emits the same first diagnostic**, verbatim. Its controls compile cleanly there —
`static const uint` as a `numthreads` argument, and a `[[vk::constant_id(1)]]` constant used
with a literal group size — so this is the feature being absent, not incomplete Clang support.

**Since the [2025-01 checklist](https://github.com/microsoft/DirectXShaderCompiler/issues/3092#issuecomment-2612831968),**
item 3 has landed: #7378 "[SPIRV] Refactor OpExecutionModeId" (e866b4bac). As a result
`LocalSizeId` is now reachable from inline SPIR-V — `vk::ext_execution_mode_id(38, TGSIZE_X, 1u, 1u)`
with `-fspv-target-env=vulkan1.3` compiles and emits:

```
OpExecutionMode %main LocalSize 1 1 1
OpExecutionModeId %main LocalSizeId %TGSIZE_X %uint_1 %uint_1
```

Not a substitute: `[numthreads]` is still mandatory on a compute entry point, so the module
carries both execution modes. It passes DXC's bundled SPIR-V validation; I have not tested it
on a driver.

Items 1 and 2 remain open HLSL spec questions. The compute-derivatives coupling is still in the
code — `addDerivativeGroupExecutionMode` picks the quad layout by reading back the
already-emitted `LocalSize` operands (`SpirvEmitter.cpp`). Nothing measured here bears on what
the answer should be. #7084 (draft) and #7439 (`Fixes #3092`) are both still open.

**Labels:** suggest adding `enhancement` and `hlsl-next`, keeping `spirv` — the remaining
blocker is a language spec decision rather than an implementation defect.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3377](https://github.com/microsoft/DirectXShaderCompiler/issues/3377) Access violation (silent, no error messages generated) when trying to build pixel shader

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3377](https://github.com/microsoft/DirectXShaderCompiler/issues/3377).

**Still reproduces on `main` (1.9.0.5433, `ab5400907`), and on every one of the 20 release
binaries from v1.4.1907 (2019-07) to v1.9.2607.** The oldest predates the report by 18 months
and already fails. The repro in the body works exactly as filed, with no edits.

```
$ dxc -T ps_6_0 -E main_fragment repro.hlsl
Internal compiler error: Terminal Error 0x80000003
```

That is all a plain run prints — the assert text goes to `OutputDebugString`. Under `cdb`:

```
Error: 	!(argIdx < endArgIdx)
File:
C:\...\lib\Transforms\Scalar\ScalarReplAggregatesHLSL.cpp(4791)
Func:	AllocateSemanticIndex.
	arg index out of bound
```

reached as `SROA_Parameter_HLSL::flattenArgument` → `allocateSemanticIndex` →
`AllocateSemanticIndex` (recursing four deep) — @Dwedit's 2021 frames, in the same order.

### The reported release crash and this Debug assert are the same failure

Releases are Release builds, where `DXASSERT` is `do { } while (0)`
(`include/dxc/Support/Global.h:356`), so a quiet release binary is not evidence of a fix.
Continuing past the traps under `cdb`, which then runs what a release build runs, reaches
`STATUS_HEAP_CORRUPTION` and dies in `memcpy` under
`DxilParameterAnnotation::AppendSemanticIndex` ← `AllocateSemanticIndex` ← `allocateSemanticIndex`
← `flattenArgument` — @Dwedit's stack frame for frame, including "crashes in a memory copy".

### Smaller repro

@damyanp's 2024 reading holds, and reduces further — no matrix, no `SamplerState`, no second
entry point, and `uniform` is not needed either:

```hlsl
float4 main_fragment(Texture2D<float4> decal : TEXUNIT0) : SV_Target {
  return decal.Load(int3(0, 0, 0));
}
```

Same assert, same line, same frames. In everything tested, the trigger is a semantic on a
resource-typed entry-point parameter.

**Both spellings fail.** Remove the `: TEXUNIT0` and DXC asks for it back:

```
error: Semantic must be defined for all parameters of an entry function or patch constant function
```

(exit `0x80004005`, identical on v1.4.1907, `main` and v1.9.2607).

### Both attempted fixes lapsed

Two PRs reference this issue and neither landed:

- **#4538** "Add extra type null checking to prevent AV" (Jul 2022) — closed unmerged Mar 2024.
- **#4554** "param validation for uniform / resources in entry point functions" (Jul 2022),
  whose body says *"This was causing AV problems as described in #3377"* — closed unmerged
  Feb 2025: *"Merge conflicts, and according to @Tex3D it seems like this is the wrong
  direction"*.

Nothing has replaced them.

### One note for anyone matching on output

Across 10 runs each on four builds, all 40 failed; none printed a source diagnostic or emitted
DXIL. **8 of the 20 release captures have empty stderr** (v1.4.1907, v1.5.2010, v1.7.2308,
v1.8.2405, v1.8.2502, v1.8.2505, v1.8.2505.1, v1.9.2602), and v1.8.2502 alternates run to run
between a silent `0xC0000409` (`STATUS_STACK_BUFFER_OVERRUN`) and a `0xC0000005` with a message.
Exit status is the only reliable signal.

FXC 10.1 compiles the body's shader as `ps_5_0` with exit 0, so the report's opening comparison
also still holds.

Compiler Explorer: **https://godbolt.org/z/rqvfvYc93** — FXC succeeds; `dxc_1_6_2112` and
`dxc_trunk` both `SIGSEGV`. CE builds are Release and Linux, so the assert cannot appear there;
the page shows the post-`NDEBUG` consequence and corroborates the Debug build rather than
standing in for it.

Labels: keep `bug`, `crash`, `incorrect-code`; consider adding `diagnostic` (the resolution both
@tex3d and @damyanp point at is to reject this rather than crash on it) and `fxc-disagrees`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3693](https://github.com/microsoft/DirectXShaderCompiler/issues/3693) Vector element index out-of-bounds not leading to compile error

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3693](https://github.com/microsoft/DirectXShaderCompiler/issues/3693).

Still reproduces on `main` (1.9.0.5433, ab5400907), and on every release back to v1.6.2104
(the oldest that accepts `lib_6_6`).

**DXC already has this diagnostic, but does not reach it in this position.** Hoisting the
access out of the subscript makes the same compiler reject the same expression:

```
error: vector element index '3' is out of bounds
    const uint oob = indices[3];
                             ^
```

In `g_vertices[indices[3]]` the out-of-bounds element becomes `undef`, which is then used as
the buffer index:

```
call %dx.types.ResRet.f32 @dx.op.rawBufferLoad.f32(
    i32 139, %dx.types.Handle %31, i32 undef, i32 12, i8 7, i32 4)  ; line:124 col:118
```

Validation passes.

Across eleven positions, the front end diagnoses every one — local initializer, call argument,
assignment target, arithmetic operand, `.w` swizzle — except **when the access is the index
operand of another subscript**. That hole is not vector-specific: `g_vertices[a[3]]` on a
3-element *array* behaves identically, while `uint x = a[3];` errors with
`array index 3 is out of bounds`. When the resulting `undef` stays inside the shader the DXIL
validator sometimes catches it late (`Access to out-of-bounds memory is disallowed`), but when
it becomes a resource index, as here, nothing objects.

Source-wise the check is in `CheckHLSLArrayAccess`
(`tools/clang/lib/Sema/SemaHLSL.cpp:16904`), which recurses into `getArg(0)`, the object
being subscripted, but never into `getArg(1)`, the index.

Repro: https://godbolt.org/z/7KGrq6xMe (restated as a compute shader so FXC can compile it —
the behaviour is the same).

- **FXC** rejects it: `error X3504: array index out of bounds`, both in this position and
  hoisted.
- **clang-dxc trunk** accepts *both* forms — no diagnostic even for the hoisted
  `uint oob = indices[3];`, and the load index becomes `poison`. As a control, the same
  shader written with `indices.w` does error there
  (`vector component access exceeds type 'const uint3'`), so this is a real gap in the new
  front end rather than the flags being ignored. Possibly worth an issue there.

One note for anyone spot-checking the attached `DefaultRT.zip`: it uses
`RootFlags(XBOX_RAYTRACING)`, which public dxc rejects outright — the resulting error is the
root signature parser, not this bug. Replacing that token with `0` compiles the file
unchanged otherwise.

Whether this should be an error or a warning, and whether the check should cover statically
out-of-range indices generally, is a language/product call.

Suggested labels: `fxc-disagrees`, `incorrect-code`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- **Sampling is unrepresentative and doubly filtered.** Oldest-first *and* hand-mixed by
  subsystem. Nothing here is a statement about the backlog.
- **The batch is temporally narrow.** Four of five issues were filed between 2020-05 and
  2021-04, and three of those within a fourteen-week span. Ages this tightly clustered mean the
  bisection results share a release-history segment, so "always reproduced" and "regressed in
  v1.6.x" are not independent observations across the batch.
- **Two of five are PIX-pass issues invisible to `dxc.exe`.** #2922 and #2923 were filed six
  minutes apart by the same engineer against the same subsystem, and #2918 in batch 007 makes
  three. **A third of the two batches' combined findings come from one reporter's afternoon in
  May 2020.** The tooling lessons that came out of them (harness-as-compiler, `dxopt -external`,
  the component cross-probe) are correspondingly specific to that subsystem, and a batch of
  ordinary shader-compile bugs would have produced far fewer.
- **#2922's `close-fixed` rests on a prose-only repro.** The issue gives no shader; the
  measurement uses `PixStructAnnotation_FloatN`'s in-tree test shader, which is what the issue
  points at. The verdict is a measured behaviour change in the pass, not a re-run of the
  reporter's case.
- **#2922's attribution is a 248-commit window, not a bisect.** `c0676c7ca` was **not built in
  isolation**. Three commits in the window touch the file. Strong, not certain, and labelled
  that way in the notes, the summary, and the draft.
- **#2922's `bisect` line says `regressed-in v1.6.2104` and means nothing of the sort.** The
  predicate asserts a **precondition**. `reindex` would re-derive it. The `history` field opens
  with a capitalised warning; anyone reading the DB rather than the notes must see it.
- **#2923's repro is agent-constructed and does not reproduce at the release current when the
  issue was filed.** This is the batch's most important single caveat and the draft leads with
  it. The scenario is broken today; whether it is the reporter's 2020 instance is unknown and
  unknowable from what was filed.
- **#2923's regression window was not bisected to a commit** and no commit is named anywhere in
  the draft, per the orchestrator's instruction. Nine candidates, five touching the likely file.
- **#3092's "not a substitute" claim about `OpExecutionModeId` passes DXC's bundled validation
  and was never run on a driver.**
- **#3092's #4128 duplicate finding is unmeasured.** Nothing was compiled for #4128; the claim
  is that the two issue *texts* ask for the same thing.
- **#3377's `cdb` work is a Debug binary emulating `NDEBUG` via `gh`, not a Release build.** It
  reproduces the reporter's stack frame for frame, which is strong, but it is emulation.
- **#3377's minimization claim is scoped to what was tested** — two spellings of one parameter
  shape. Other shapes were not enumerated.
- **#3693's repro is `partial`.** The attachment needed a platform token neutralised
  (`RootFlags(XBOX_RAYTRACING)` → `0`) to run at all, and the CE link publishes a compute
  restating rather than the raytracing original, because FXC has no raytracing profile.
- **`reindex` was not run**, per the brief. Combined with the fact that `audit` does not
  re-score, **no probe in the corpus was re-scored during this collation**, so none of the
  method lessons above was applied retroactively to earlier batches. They take effect from
  batch 009.
- **`scripts/` and `SKILL.md` were changed by this collation** — unlike batch 007, which
  reported everything and implemented nothing. `test_predicates.py` passes with 7 new
  assertions; `audit` and `audit --collated` both exit 0. The `godbolt` changes were verified
  against the live CE API but **`triage.py godbolt` was not re-run for any issue in this batch**,
  because that would publish a new short link and invalidate the four verified ones. The
  full-pane capture file therefore does not yet exist for these five issues.
- **`overview.md` was regenerated after `reviewed_by` was set on all five**, because `audit`'s
  staleness gate compares it against the newest `verdict.json`.
- **The tree is deliberately left dirty.** Nothing was committed or pushed.

## Suggested next step

1. **Look at #4128 and #3092 together.** One is closed `NOT_PLANNED`, the other is open with an
   open `Fixes` PR, and they ask for the same thing. This is the cheapest action in the batch
   and it is not a triage verdict — a maintainer decides which one lives.
2. **#3377 needs a direction, not a fix.** Both attempts were rejected, the second explicitly as
   "the wrong direction" per @Tex3D. The triage cannot supply that and the draft does not try.
   It is a five-year-old always-reproducing access violation with an eight-line repro; it
   deserves the decision more than it deserves another patch.
3. **Decide #2922 before #2923.** They are adjacent in code and resolve in opposite directions;
   closing #2922 as fixed while #2923 stays open is the correct outcome and will look wrong to
   anyone who reads only the titles. If both drafts are posted, post them together.
4. **Finish the `bisect` half of carried-over item 2**, re-scoped: let a predicate declare that
   it asserts a *precondition*, and make `bisect` refuse to narrate a history from it. #2922 is
   the second consecutive batch where the `bisect` line means the opposite of what it says, and
   a capitalised warning in a `history` field is not a fix.
5. **Consider whether `triaged_with_commit` should store the tree hash.** This batch spent real
   effort proving a build was valid after its SHA vanished. The tree hash is stable under a
   message rewrite and would have made that self-evident.
6. **Break the temporal cluster in batch 009.** Four of these five were filed inside eleven
   months, and two of them six minutes apart. Whatever selection rule produced that should be
   loosened, or the next batch's method findings will again be a property of one subsystem in
   one year.
