# DXC issue triage — batch 006

**Ground truth:** clean `main` **Debug** build, source-identical to upstream
`13730886e`. The binary self-reports
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`;
that fork-local SHA is captured evidence, not the public citation.
**History:** 20 official release binaries, v1.4.1907 → v1.9.2607.
**FXC comparisons:** real `fxc.exe` from the Windows SDK.
**Nothing was posted, edited, labelled or closed. No DXC source was modified**
(`git diff upstream/main..HEAD -- . ':(exclude).github/skills/**'` is empty, and so is
`git status` outside the skill directory).

> **The compiler did not change between batch 005 and batch 006.** `git fetch upstream main`
> showed 0 commits ahead of HEAD, so the batch-005 build represented by `13730886e` was still current; the
> rebuild *check* was performed and its result recorded rather than the rebuild being skipped
> silently. Batch 005 and batch 006 verdicts are therefore directly comparable. Batches 001–004
> measured `eff900d5` and are not.

> ### ⚠ The review gate was suspended for this batch, and that is a real reduction in safety
>
> `SKILL.md`'s hard rules say *"Triage a handful of issues, then stop and let a human review
> before continuing. Verdict quality degrades silently; unattended full passes hide that."*
> The maintainer was asked directly and chose to run batches **006–010 continuously**, with an
> emailed summary after each acting as an **asynchronous** checkpoint rather than a blocking one.
>
> What partially compensates: each batch is committed and pushed separately so a bad one can be
> reverted alone; collation is a fresh session that cannot inherit an earlier batch's
> assumptions; step 10's independent review still runs on a different model; `audit` gates on
> evidence completeness and overview staleness. **None of those checks whether a verdict is
> true.**
>
> **Collation's honest read on whether quality slipped in batch 006: no, and there is evidence
> rather than an impression behind that.** `reindex` re-scored all 30 issues and 452 runs with
> no disagreement, no stale command and no control-expectation failure. The step-10 review found
> **nine factual errors across five drafts** — the highest count of any batch — but every one was
> a *drafting* error (a mis-attributed number, a fabricated line inside a "verbatim" block), and
> none of them changed a verdict. Two of the five workers went looking for their own tooling to
> be wrong and demonstrated it with committed, re-runnable probes. That is the opposite of the
> degradation the gate exists to catch. The count to watch across 007–010 is the *nine*: if
> drafting errors keep rising while the review keeps catching them, the review is carrying the
> batch, and that is exactly the silent slide the rule warns about.

## Headline

**All five reproduce. None is closable. Every one has always reproduced, as far back as it is
possible to check.** That uniformity is a property of the sample, not of the backlog — see
[Caveats](#caveats).

**#2331's own text is stale in two of its three body claims, and the main claim still holds.**
This is the batch's highest-value finding, and it is the dangerous shape: someone spot-checking
the *secondary* claims today finds them both wrong, and could reasonably conclude the whole
2019 report is obsolete. It is not. Commenting out a case and adding a fourth enumerator now
stop at Sema with `error: control may reach end of non-void function [-Wreturn-type]` instead of
reaching the DXIL validator — a change between v1.4.1907 and v1.5.2010 — but the reported defect
itself (an exhaustive `switch` over an `enum class` in a non-void function lowers the
fall-off-the-end path to `unreachable`, which DXIL disallows) fails validation on **every one of
the 21 probes**, `main` included.

**The batch's designed experiment came back negative, and the negative is the finding.** #2792
was chosen because its symptom is a *missing diagnostic* — the inverse of #3055's shape, which
is what batch 005 rewrote the `invalid-probe` classifier for. The classifier did **not**
misbehave: 21 primary probes and 5 controls, zero demotions. The reason inverts the expectation
and is the generalisable part: *the symptom of this issue is the absence of all diagnostics, and
its reproducing probes are clean exit-0 compiles — there is no diagnostic text for a
feature-absence marker to collide with.* **Classifier exposure depends on whether the
reproducing case is noisy or silent, not on whether the issue is "about diagnostics".**

**Going looking anyway found two real defects in the same code.** `classify`'s absence guard
demotes only on a feature-absence marker or an internal failure — an *ordinary diagnosed error*
(on Windows, E_FAIL plus an `error:` line, the likeliest early failure across twenty releases) is
neither, so an unanchored absence predicate scores it a textbook reproduction. Demonstrated
against real captured output, not a mock. #2792 was safe only because its author anchored the
predicate. **Fixed here as a capture-time warning with eight new tests**; a demotion was
considered and rejected, because it would be #3055's defect in a new shape.

**#3251 and #3259 are related, not duplicates — re-derived independently and it holds.** Batch
005 predicted from source that #3251 still traps on `main` but in `TranslateCBAddressUserLegacy`
rather than `WrapInArrayTypes`. #3251's worker, **told nothing about #3259**, measured exactly
that: `DXASSERT(0, "not implemented yet")` at `HLOperationLower.cpp:8801`, reached through
`DxilGenerationPass::GenerateDxilOperations`. `duplicate-of` still has zero rows across 30
issues and still correctly so.

## Summary

| # | Title | Repro | Status | History | Action | Link |
| --- | --- | --- | --- | --- | --- | --- |
| [#2128](https://github.com/microsoft/DirectXShaderCompiler/issues/2128) | Generated bytecode has very higher compression ratio | agent-constructed | **repros** | always; ratio flat 0.523→0.568 across all 20 releases | not a bug — encoding decision | *(none — [skip recorded](#2128--the-symptom-is-a-quantity-and-the-tooling-has-no-word-for-that))* |
| [#2331](https://github.com/microsoft/DirectXShaderCompiler/issues/2331) | Problem with DXIL signing and switch case/enum use | complete | **repros** | always, all 21 probes v1.4.1907→`main` | keep open | [nEqsn9nEW](https://godbolt.org/z/nEqsn9nEW) |
| [#2528](https://github.com/microsoft/DirectXShaderCompiler/issues/2528) | Remainder of `inout` signature element not passed through | complete | **repros** | always, all 20 releases, **both** predicates | keep open | [EaYncchW3](https://godbolt.org/z/EaYncchW3) |
| [#2792](https://github.com/microsoft/DirectXShaderCompiler/issues/2792) | Need to report error when offset bigger than root constant size | complete | **repros** | always; all 20 exit 0, no invalid probes | enhancement, not a bug | [d5zcrTPjP](https://godbolt.org/z/d5zcrTPjP) |
| [#3251](https://github.com/microsoft/DirectXShaderCompiler/issues/3251) | Missing implementation for `HLOpcodeGroup::NotHL` in `TranslateCBAddressUserLegacy` | complete | **repros** | always v1.5.2010+ (19 of 20; v1.4.1907 a genuine `invalid-probe`) | keep open | [arjrMWhWf](https://godbolt.org/z/arjrMWhWf) |

Confidence is `high` on all five. **`text_stale` is set on #2331 only** — #2528 and #3251 each
considered it explicitly and rejected it, which is recorded below because a field that gets set
out of enthusiasm stops meaning anything. All four CE links were re-fetched from
`https://godbolt.org/api/shortlinkinfo/<id>` during collation and resolve to the panes claimed
(#2331 and #3251: `dxc_1_6_2112` + `dxc_trunk`; #2528: `fxc_10_0_19041` + both DXC; #2792: both
DXC + `hlsl_clang_trunk`). Drafts were written by `claude-opus-4.6` (#2128, #2331, #2792) and
`claude-opus-5` (#2528, #3251); all five were reviewed by `gpt-5.6-sol`.

**Consistency check between `notes.md`, `verdict.json` and the DB: clean.** Every verdict row
matches its notes; `reindex` re-scored 30 issues and 452 runs and reported only the five
expected *"verdict.json has no reviewed_by"* messages, which the per-issue sessions were
instructed to leave for collation. Three cosmetic divergences and two pieces of silent
PowerShell string damage were found, and are recorded under
[what this batch taught us](#16-powershell-silently-damaged-two-artifacts-and-three-cosmetic-record-inconsistencies-new).

## Per-issue findings

### #2128 — the symptom is a *quantity*, and the tooling has no word for that

**Verdict: reproduces, always has, and is not a defect.** DXC objects deflate to **3.7×** fxc's
for the same shaders. The reporter's 2019 numbers essentially hold: fxc's ratio measures 0.33
against their ~0.30; DXC with `-Qstrip_reflect` measures **0.771** against their 0.80–0.85.

The mechanism is measured, not assumed: **the DXIL part alone** deflates to **0.848** (in the
reported band) and **0.900** (just above it), because LLVM 3.7 bitcode is bit-packed and close
to entropy-dense, where DXBC's `SHEX` part is byte-aligned repetitive tokens that deflate to
**0.271**. Raw sizes are much closer than zipped ones — on the representative pair DXC is 2.0×
fxc raw but 3.7× zipped — so the gap is overwhelmingly compressibility, not volume.

**Half of BitMD's 2019 comment landed and half did not, and the split is the interesting part.**
Reflection metadata *did* move out of the module into a separate `STAT` part between v1.4.1907
and v1.5.2010, cutting corpus size 39% raw and 34% zipped. The bitcode's *compressibility* never
followed: 0.839 → 0.851 → 0.848 across the same span, and a 20-release linear scan finds the
corpus ratio between **0.523 and 0.568** throughout with no transition anywhere.

**Division's 2022 question is answered:** PC DXC has no shader-object compression to disable.
`ZlibCompressAppend` has exactly two call sites — the PDB writer (`DxilPdbInfoWriter.cpp:31`) and
the `SRCI` source part (`dxcshadersourceinfo.cpp:425`) — neither of which touches the shader
object the Xbox macro is about.

**This is the first issue in six batches whose symptom cannot be written as a predicate at all**,
and it is `unscored` rather than forced into one. See method note 1.

**No Compiler Explorer link, deliberately.** `godbolt_skip` is recorded on the verdict with the
reasoning: CE panes show text disassembly, and no pane can display an object's byte count or run
deflate. A link would show fxc, DXC and Clang all succeeding — published bare, that reads as
*"cannot reproduce"*, which is the #2191 trap, and here without even #2191's partial value. A
Clang pane was considered and rejected: Clang's HLSL path emits the same LLVM bitcode encoding
and so *inherits* the property, but a text pane still cannot show it. The shareable artefact is
`measure.py`, committed in the issue directory, whose verified output is
`manual-case-compression.txt`.

### #2331 — the report is stale in two places, and still correct in the one that matters

**Verdict: reproduces on `main` and on every release back to the v1.4.1907 floor — 21 probes,
21 reproductions, 0 invalid.** A `switch` over an `enum class` covering every enumerator, with no
`default:`, in a non-void function, lowers the fall-off-the-end path to an LLVM `unreachable`.
DXIL disallows that instruction, so validation fails with `Instructions must be of an allowed
type` (E_FAIL 0x80004005 — an error, not a crash). Adding `default:` compiles clean, which is the
workaround and body claim B3, and it still holds.

**⚠ `text_stale`.** Body claims B1 and B2 no longer describe the compiler:

| claim | 2019 | today |
| --- | --- | --- |
| B1: comment out one `case` | "validates clean" | `error: control may reach end of non-void function [-Wreturn-type]` at **Sema** |
| B2: add a fourth enumerator | reaches the validator | same `-Wreturn-type` error at **Sema** |
| B3: add `default:` | compiles clean | **unchanged** |

The change lands between v1.4.1907 and v1.5.2010, attributed to `8c43a1456` within a 434-commit
window. Dating it required a hand-written loop over `run` — see method note 6.

**Signing is not implicated, despite the title.** Validation fails, so nothing is ever signed.
The reporter's `DXIL.dll not found` warning is environmental: that text has been absent from the
source since `77b2ff676`, and `dxc.exe` loads an external validator only when `DXC_DXIL_DLL_PATH`
names an absolute path (`lib/DxcSupport/dxcapi.extval.cpp:433-462`). The digests were measured
rather than reasoned about — `main-debug` default and `DXC_DXIL_DLL_PATH`-forced produce
**identical** digests at offset 4 of the `DXBC` header; `-Vd` yields all zeros (unsigned);
v1.4.1907 and v1.9.2607 differ from each other. That table lives in
`manual-case-signing.txt` and **only** there, which is method note 5.

Maintainers' 2024 position is won't-fix-in-DXC / handled in Clang, and Clang trunk emits no
`unreachable` for a cut-down form of the same construct — measured, with a #1702-style control
showing Clang also fails on inputs DXC accepts, so the clean pane is not read as an endorsement.

### #2528 — the loud case is the lucky one; the silent case is the impact

**Verdict: reproduces on `main` and all 20 releases, under *two* predicates (42 probes).**
Writing one component of an `inout` signature element suppresses the pass-through of the rest.
For `void main(inout float4 pos : SV_Position) { pos.w = 1; }` at `vs_6_0`, DXC emits only
`storeOutput(i32 5, i32 0, i32 0, i8 3, …)`, **no `loadInput` at all**, and the output signature
reads `Used=w` instead of `xyzw`. FXC passes all components through on byte-identical sources.

**The finding this batch adds is not in the issue text and is not a staleness finding — it is an
addition.** On `SV_Position` the DXIL validator catches the malformed signature and the compile
fails, which is why the issue reads as a compile error. On an *ordinary* varying (a struct with
`TEXCOORD0`) **DXC exits 0 and emits a shader whose `.yzw` are undefined.** That is the impact
evidence the 2024 dormancy note was missing, and it is why `text_stale` was considered and
**rejected**: the issue's text is accurate, it is just narrower than the defect.

Capturing both halves needed a *second* `cmd.txt` line rather than a changed one, and a second
`match-varying.json` rather than a wider predicate — see method notes 7 and 8.

**No Clang pane, and a control is why.** Clang's vertex support parses the shader but its
backend cannot lower signature I/O (`Unsupported intrinsic llvm.dx.load.input.v4f32`), and the
`SV_Position` `inout` error fires on the known-good control too. A pane would be pure noise —
#1702's trap in a stage `SKILL.md` did not previously list. It now does.

### #2792 — the check has never existed, in any probed release

**Verdict: reproduces on `main` and all 20 releases; every probe exits 0.** No DXC has ever
compared a cbuffer's size against its root constant block's `num32BitConstants`.
`RootConstants(b0, num32BitConstants = 1)` with a two-float cbuffer at `b0` compiles clean, with
no diagnostic, and codegens the out-of-bounds read
(`extractvalue %dx.types.CBufRet.f32 %2, 1`).

**The sharpest piece of evidence is a null result.** Setting `num32BitConstants = 2` — making the
shader correct — produces **identical disassembly and the same shader hash**. The field is
parsed, serialised and printed, and read by no validator: `DxilRootSignatureValidator` registers
a root constant as a one-register CBV range without passing `Num32BitValues` at all.

**It is a gap in a check that runs, not the absence of one.** Binding `b1` against a `b0`
cbuffer *is* rejected (`Shader CBV descriptor range … is not fully bound in root signature`).
That check, `VerifyRootSignatureWithShaderPSV`, works from PSV bind info, and
`PSVResourceBindInfo0` (`DxilPipelineStateValidation.h:240`) carries no size — so it cannot make
this comparison from the data it reads today. A front-end check faces no such constraint.

`hlsl_clang_trunk` does not diagnose it either — **but it also accepts the `b1`/`b0` mismatch
DXC rejects**, so its silence is *"not implemented there either"* rather than an independent
judgement. That distinction exists only because the worker ran a control on a *clean* Clang pane;
see method note 10.

**Proposed: remove `bug`, add `diagnostic`, `enhancement`, `check-in-clang`.** This is a request
for a diagnostic that has never existed, not a regression. The draft hedges the removal
explicitly, as `SKILL.md` step 8 requires.

### #3251 — same defect, four failure shapes, and eight releases that look like a syntax error

**Verdict: reproduces on Debug `main` and on all 19 probeable releases.**
`DXASSERT(0, "not implemented yet")` at `lib/HLSL/HLOperationLower.cpp:8801` in
`TranslateCBAddressUserLegacy`, exit `0x80000003`. The reported mechanism is unchanged:
`p.lhSampleData = g_lhSampleData` becomes one `llvm.memcpy` out of the legacy cbuffer, whose
`HLOpcodeGroup` is `NotHL`, and the cbuffer-user walker has no case for it.

**Only the line number moved, and the move is dated.** 6207 was the `CallInst` arm's final
`else`; PR #3034 (`eaa7f95d0`, six days after filing) inserted an `IntrinsicInst` branch, so the
memcpy now reaches its inner `else` at 8801 (the outer one is 8804, identical text). Line drift
alone was judged **not** worth `text_stale` — a correct diagnosis pointing at a line that moved
is not a stale report, and setting the field for that would dilute it.

**Scoped in both directions.** Not `$Globals`-specific: an explicit `cbuffer` block traps too. Not
payload-agnostic: the same copy into an `RWStructuredBuffer` at `cs_6_0` compiles clean. It is
the `DispatchMesh` payload that keeps the copy a `memcpy` into DXIL lowering. A field-by-field
copy compiles clean on `main` and back to v1.5.2010, and is a workaround.

**v1.4.1907 is a genuine `invalid-probe`, confirmed with a feature-presence control** — it
predates `as_6_5` and never ran the repro. v1.5.2010 is three weeks *older* than the report, so
19 releases covers the issue's entire life.

**The 19 reproductions arrive in four shapes**, which is why this issue is proposed below as a
permanent fixture: access violation `0xC0000005` (9, one with completely empty output),
`DXC_E_LLVM_UNREACHABLE 0x80AA001C` in `DataLayout::getTypeSizeInBits` (2), E_FAIL with
`UNREACHABLE executed` (7), and E_FAIL with `llvm::cast<X>() argument of incompatible type` (1).
**Eight of nineteen exit with the same status as a syntax error**, so a message-keyed predicate
would have reported this fixed for eight releases.

**Not an `NDEBUG` artefact.** With the assert compiled out, the leftover memcpy's operand is
deleted anyway and release builds access-violate. That prediction was made *before* the scan ran,
by walking the Debug build past its asserts under `cdb` — see method note 12.

## Cross-issue analysis

### Relationships

**No duplicates. `duplicate-of` still has zero rows across 30 issues.**

**#3251 ↔ #3259 (batch 005) — related, not duplicates. Independently re-derived, and it holds.**
Batch 005 captured #3251's repro into #3259's directory (`crossref-3251-cbuffer-payload.hlsl`,
`variant-crossref-3251-main-debug.txt`) and predicted from source that it would still trap on
`main`, in a different pass. #3251's worker — who was deliberately **not told** this — measured
the same thing from the other side and sharpened it:

| | #3259 | #3251 |
| --- | --- | --- |
| assert | `WrapInArrayTypes`, `DxilUtil.cpp:877` | `DXASSERT(0, "not implemented yet")`, `HLOperationLower.cpp:8801` |
| function | `TranslatePtrIfUsedByLoweredFn` | `TranslateCBAddressUserLegacy` |
| pass | `SROA_Parameter_HLSL` | `DxilGenerationPass::GenerateDxilOperations` |
| trigger | payload contains an HLSL object type, so `GetLoweredUDT` returns `nullptr` | payload filled by a whole-struct `memcpy` out of a **legacy cbuffer**; no object type needed |

Same reporter, same week, same `as_6_5` + `DispatchMesh(1,1,1,p)` shape; different assert,
different pass. **Fixing either will not fix the other.** Two isolated observers agreeing is
stronger evidence than one saying it twice — the same standard batch 005 applied to #2530/#2188.

**#3251's discarded control surfaced an apparently unreported third defect.** `as_6_5` with the
payload filled from a *local* struct traps at `!(onlyUsedByLifetimeMarkers(BCI))`,
`ScalarReplAggregatesHLSL.cpp:2630`, in an **earlier** pass than either of the above. Evidence:
`variant-local-payload.hlsl` and CASE 3 of `manual-case-assert-stack.txt`. **Someone should check
whether an issue exists for it.** It is not claimed in any draft.

**#2792's mechanism generalises to any root-signature-vs-shader issue.**
`VerifyRootSignatureWithShaderPSV`, invoked from `lib/DxilValidation/DxilContainerValidation.cpp`,
is where *all* such checking lives. Any future issue about a root-signature/shader mismatch shares
this root cause and probably its fix. Flagged for batches 007–010.

**#2528's silent half may have neighbours.** "Undefined values reach the consumer with no
diagnostic" is the same class as batch 002's #3009 (`dxc silently passes uninitialized value as
undef`), though the mechanisms differ. Not claimed as a relationship — nobody measured it — but
it is the first thing to check if an unwritten-signature-component issue turns up.

**#2528 has an unwritten regression test waiting.** `inout5.hlsl` and
`fn.param.inout.stage.hlsl` both exercise `inout` stage parameters and neither covers the
partial-write case, so the issue's own `RUN:`/`CHECK:` block is still unwritten work. Recorded,
not proposed — proposing work is not this skill's job.

**#2128 has no cross-references at all.** 23 timeline events, no `cross-referenced`, no linked
PR, no milestone-carrying commit — so unlike #2427 there is no lapsed resolution to check.

**#2331 points at an unlinked Clang issue.** @llvm-beanz's 2024 comment refers to an issue he
filed against Clang to remove these instructions during DXIL lowering. It is not linked from
#2331 and was not searched for. If Clang's clean behaviour on the cut-down form *is* that work
having landed, #2331's disposition depends on it and the two should be linked. Someone with the
number should check; the draft claims only what was measured.

### Bearing on earlier batches

- **#2202's three stale variant headers, carried over from batch 005, are cleared.** The
  orchestrator ran `reindex --accept` as batch 005's report recommended. Exactly the three
  predicted files changed and **only their headers** — two re-scored `invalid-probe` on the
  HLSL-2021 marker `for non-scalar types use 'select'`, one because the probe failed internally.
  No captured output, command line or exit status was altered, and #2202's issue-level verdict is
  unaffected. Batch 005's `# invalid-probe-reason:` line is what made this checkable at a glance.
- **Batch 005's prediction about #3251 was correct in every particular** (see above). That is the
  first time a batch report has made a falsifiable prediction about a *future* batch's issue and
  had it independently confirmed.
- **No earlier verdict is believed to be wrong.** `reindex` re-scored all 452 runs across all six
  batches with no disagreement.

### Patterns across the five verdicts

1. **Five of five reproduce and five of five have *always* reproduced.** No batch has been this
   uniform. Read it as a property of oldest-first sampling, not of DXC.
2. **Two of the five are not bugs in the sense their labels claim.** #2128 is a container-encoding
   consequence; #2792 is a feature request for a diagnostic that never existed. Both were filed as
   defects and both are legitimate — the label is what is wrong, not the issue.
3. **Only one issue in five is stale in its text**, against three of five in batch 005. The
   difference is instructive: batch 005's issues were *recent* and had moved under their authors;
   batch 006's are 2019–2020 and describe defects nobody has touched since.
4. **Every issue needed at least one control, and on two of five a control changed the
   conclusion** — #2792 (Clang's clean pane means "unimplemented", not "correct") and #2528
   (Clang's vertex failure fires on the known-good control too). Batch 005 said this about
   *absence* clauses; batch 006 extends it to *clean* comparison panes.
5. **The two oldest issues in the batch are design questions and the three newest are omissions
   in checking or lowering.** The same split batches 001–005 saw. Still a sampling artefact.

## Proposed label changes

None are applied. All are recorded proposals, validated against the live 58-label taxonomy.

| # | Current | Proposed | Why |
| --- | --- | --- | --- |
| #2128 | `dxil`, `revisit-sooner` | add `fxc-disagrees`, `enhancement` | measured against real FXC and they differ by 3.7×; the ask is a container-encoding change, not a defect fix |
| #2331 | `bug` | add `validation`, `incorrect-code` | the failure is a DXIL validation rejection of code DXC itself emitted |
| #2528 | `bug`, `fxc-disagrees` | add `correctness`, `check-in-clang` | the silent case emits a shader with undefined components; resolution touches signature lowering, which Clang is rewriting |
| #2792 | `bug` | **drop `bug`**; add `diagnostic`, `enhancement`, `check-in-clang` | no probed release has this check; it is a request for a new diagnostic, and Clang has no root-signature-vs-shader checking at all yet |
| #3251 | `bug`, `crash` | no change | already correct |

## What batch 006 taught us about the method

### 1. The predicate vocabulary cannot express a symptom that is a *quantity* (new)

#2128's symptom is a byte ratio. `match.json` speaks only of stdout, stderr and exit codes, so
there is nothing to write. The issue is `unscored` and `bisect` is inapplicable — and that is
**correct**, not a gap papered over.

What replaced it is the transferable part: a **falsifiable rule stated in `expected.md` before
measuring**, evaluated by a committed script (`measure.py`), whose output is captured as
`manual-case-compression.txt`. That is a predicate in everything but vocabulary — pre-committed,
re-runnable, and wrong-able.

### 2. A quantity has no `bisect`, but its history is still cheap (new)

There is no numeric analogue of `bisect --linear`, but a **linear scan over all 20 releases took
about a minute** and produced the strongest single fact in #2128's draft: the ratio sits between
0.523 and 0.568 for the whole range with no transition anywhere. **Do not let "the tooling has no
command for it" become "the history is unmeasurable."**

### 3. A ratio predicate can key on a denominator that moves under you (new, and it bit)

#2128's pre-committed rule — "DXC ratio ≥ 0.70" — was met at **0.771** with `-Qstrip_reflect` and
missed at **0.613** with default flags, on the same shaders. The cause: DXC now emits a separate
`STAT` part, and deflate deduplicates it against `DXIL`, so the *default-flag* ratio is a
statement about part duplication rather than about bitcode. **Pre-commit on zipped bytes for a
fixed corpus, never on a ratio whose denominator is compiler output.**

### 4. An agent-constructed corpus can bias the very number under test (new)

`corpus-large.hlsl`'s 32× `[unroll]` flattered *both* compilers — FXC reached 0.059 — and dragged
the totals with it. The fix was an explicit **"TOTAL excl. unrolled"** row rather than a quietly
adjusted corpus. Related and worth keeping: **control discipline transfers from predicates to
measurements.** #2128's measurement harness re-runs an incompressible sha256 chain (must be
≥ 0.98) and a plain source file (must be ≤ 0.50) on **every** invocation, so a broken deflate
path cannot masquerade as a finding.

### 5. There is no way to record "what the container looked like", only "what was printed" (new)

#2331's decision-relevant evidence is a table of **signature digests read from bytes at offset 4
of the `DXBC` header**. `match.json` has no artefact type for "a fact measured from an output
file", so the table lives in prose in `manual-case-signing.txt` — invisible to `audit`, absent
from `overview.md`, and unreachable by any cross-batch query. **Signing was a new code path for
this workflow and this is the gap it exposed.** Anything about container structure, part
presence, hashes or sizes is currently prose.

A related trap from the same issue: forcing the external validator changes the exit status from
`0x80004005` to **`0x80AA0009` (`DXC_E_IR_VERIFICATION_FAILED`)** and loses the source location.
**An exit-code-keyed predicate would have been wrong.**

### 6. `--expect` is per-file and `bisect --linear` runs one shader (new)

Two shapes of the same limitation, both hit on #2331:

- A variant whose *meaning flips across the release range* — matching at v1.4.1907 and correctly
  not matching after — has no single `--expect` declaration. Intent ended up spread across 21
  files and prose.
- `bisect --linear` has no "and also run these other shaders". Dating a **non-symptom** behaviour
  change (B1/B2 moving from validator to Sema) needed a hand-written loop over `run`. That is how
  the change was pinned between v1.4.1907 and v1.5.2010.

### 7. A wrong-code predicate may need a *second* `cmd.txt` line, not a changed one (new)

#2528's as-filed command fails validation and prints no DXIL — so the module that proves the
wrong-code claim is never captured. Adding `-Vd` as a **second line** puts both the diagnostic and
the module in one capture. **Replacing** the line would have destroyed the evidence that the
compile fails at all; putting `-Vd` **only in a variant** would have left `bisect` unable to
measure the wrong-code claim across releases. The two-line form is the only one that keeps both.

### 8. A second predicate is also the right tool for a second *shape* of the same defect (new)

Also #2528: `match.json` covers the `SV_Position` case and `match-varying.json` the silent
varying case, run with `run --shader X --label Y --match Z`. `SKILL.md` documents the second
predicate for a second *claim* and labels for a second *shader*; the combination — one defect,
two shapes, each with its own 21-release history — is not mentioned anywhere and should be.

A rough edge fell out of it: **`--expect no-match` on a variant that demonstrates a *wider* bug
reads as "clean"** in the summary line, when what it actually means is "this case is worse". The
declaration is right and the wording is misleading.

### 9. `classify`'s absence guard misses the likeliest early failure — **fixed here** (new)

The batch's designed experiment and its most concrete tooling outcome.

**The negative result first, because it is the finding.** #2792 was chosen to stress the
`invalid-probe` classifier on a *missing-diagnostic* symptom, inverting #3055's shape. It did not
misbehave: **21 primary probes, 5 controls, zero demotions.** The reason generalises further than
the experiment did — *the symptom is the absence of all diagnostics, and the reproducing probes
are clean exit-0 compiles, so there is no diagnostic text for a marker to collide with.*
**Classifier exposure depends on whether the reproducing case is noisy or silent, not on whether
the issue is "about diagnostics."**

**The defect found by going looking anyway.** `classify` demotes a matching absence predicate only
when the output tripped a feature-absence marker **or** `is_internal_failure` fired. On Windows an
ordinary diagnosed error is E_FAIL `0x80004005` plus an `error:` line — **neither**. Demonstrated
against real captured output, not a mock: `variant-rs-register-mismatch-main-debug.txt`
(3 `error:` lines, no DXIL) scores **`repro`** under an unanchored absence predicate.
Re-runnable via `classifier-probe.py` with the two committed predicates in `data/issues/2792/`.
**`SKILL.md`'s wording — "reclassifies such a probe as `invalid-probe` when the compile also
failed" — overstated the code.** #2792 was safe only because its author led with a positive
anchor (`extractvalue %dx.types.CBufRet.f32 <v>, 1`, which a failed compile cannot emit).

**What was done about it.** A demotion was considered and **rejected**: an issue whose symptom is
a *wrong* diagnostic errors on every reproducing probe, so demoting that case is #3055's defect in
a new shape. What is safe is to say so at capture time. Added to `scripts/triage.py`:

- `_has_positive_clause(issue, match_file)` — the companion to `_is_absence_predicate`. Counts
  uninverted `contains`/`regex`/`internal_failure`/`timeout` as anchors. **`nonzero_exit` is
  deliberately not an anchor**: a rejected input exits nonzero too, which is the failure being
  guarded against.
- A capture-time warning in `execute`, fired only when the verdict is `repro` **and** the compile
  actually failed **and** the predicate is absence-only. It changes no verdict, no header and no
  stored row.
- **Eight new tests in `scripts/test_predicates.py`**, including the `nonzero_exit` and
  inverted-clause edges. All tests pass.
- `SKILL.md`'s overstated sentence is corrected to describe what the code does, and now names
  #2792's anchor as the worked example.

**And a latent, one-directional hazard that cannot be fixed.** `_predicate_quotes` — batch 005's
#3055 fix — is **structurally unavailable** to an issue asking for a diagnostic that does not
exist, because there is no text to quote. It only bites forwards in time: a future release that
*fixes* #2792 could be demoted to `invalid-probe` if its new diagnostic happens to contain a
marker phrase. Demonstrated with the wording *"…requires shader model 6.0 or above"*. Nothing to
do today beyond knowing it.

### 10. A clean Clang pane needs a control just as much as a Clang error does (new)

`SKILL.md` already says a Clang *error* is not evidence without a control. #2792 shows the
converse matters more: Clang **does** parse and check root signatures (a malformed one errors),
but it **accepts** the `b1`/`b0` mismatch DXC rejects — so its silence on the reported issue is
"not implemented there either", not an independent opinion. Without that control the draft would
have implied Clang agrees the code is fine.

The same batch supplied a stage-support correction: **Clang parses vertex shaders but its backend
cannot lower signature I/O** (`Unsupported intrinsic llvm.dx.load.input.v4f32`), measured on
#2528, and the `SV_Position` `inout` error fires on the known-good control as well. Added to
`SKILL.md`'s stage list, which previously named only compute, pixel and geometry.

### 11. A negative control can fire the predicate *for a different reason* (new)

#3251's obvious control — payload filled from a local instead of a cbuffer — **also traps**, at
`!(onlyUsedByLifetimeMarkers(BCI))`, `ScalarReplAggregatesHLSL.cpp:2630`, in an earlier pass.
Two consequences:

- **A crash predicate is signature-blind.** `internal_failure` cannot tell one assert from
  another, so a control failure on a crash issue is not diagnosable from exit codes at all. **You
  have to get the stack.** That is what turned a discarded control into a probable third
  unreported defect.
- **`--expect` has no `match-unrelated` value.** The options are `match`, `no-match` and
  `invalid-probe`; "fires, but for a different reason" is unrecordable, so the control was
  discarded and the finding survives only in prose.

### 12. The `cdb` recipe needed the *continue-past* step, not the stack step (new, and the note overstated it)

#3251's method note says `SKILL.md`'s debugger recipe "does not cover the `__debugbreak` form of
`DXASSERT`". **Checked against `SKILL.md` and that is not right** — the `__debugbreak` stack form
(`cdb -c "g;kn 40;q"`) has been documented since batch 004, along with the quirk that
`DXASSERT` prints `File:` on the *following* line. Recording the correction because the report
should not launder a worker's claim it did not check.

**The real gap is next door and is worth having.** `SKILL.md` attributed `gh`-as-`NDEBUG`-emulation
to the C++-exception form only. It works for the trap form too: `g;gh` runs to the trap and steps
past it, and chaining more `gh`s — adding `sxe -c "gh" e0000001` for any *LLVM* assert further on,
which does throw — walks a Debug build forward exactly as a release build would. On #3251 that
produced the release prediction (*"the leftover memcpy's operand is deleted anyway, so release
builds access-violate"*) **before** the 20-release scan ran, and the scan then agreed.
`assert-stack.cmd` and `ndebug-emulate.cmd` are committed in the issue directory. `SKILL.md` now
carries both forms with the emulation property attributed to `gh` rather than to one recipe.

### 13. #3251 is a ready-made real-world fixture for the `internal_failure` rule (new)

One defect, 19 releases, **three exit statuses and four text signatures** (five counting the
Debug trap). Eight of nineteen exit plain E_FAIL — indistinguishable by status from a syntax
error — and v1.5.2010 prints **nothing at all**. Every synthetic test of `is_internal_failure`
in `test_predicates.py` today is hand-written text. This is the same rule exercised by evidence
nobody composed for it. Recommended for adoption as a regression fixture.

### 14. Smaller tooling defects, all measured

| # | Defect | Status |
| --- | --- | --- |
| #2128 | `run --shader X` is incompatible with an `-Fo` in `cmd.txt` — `retarget_cmd` replaces only the source operand, so every shader writes the same output file | **open**, worth a warning |
| #2792 | `fetch` reports "no code block" where the body **is** a runnable repro (250 chars, unfenced). `prose-only` should mean *no source supplied*, not *no fenced block* | **open** |
| #2792 | `cmd-as-filed.txt` is for a **stated** command that was changed, not for one that had to be supplied. #2792 states none, so the file was correctly not written — but `SKILL.md` does not say so | **open**, one line |
| #2331 | `godbolt-note.txt` must not contain `//` markers: `annotate()` (`triage.py:1420-1433`) prefixes them itself, producing `// // What to look for`. The first published link `WGoj357v3` is superseded by `nEqsn9nEW` | **avoided**; reading back `/api/shortlinkinfo/<id>` is a cheap, complete step-7 verification and caught it |
| #2331 | `labels --refresh` does `DELETE FROM labels` then re-inserts (`triage.py:1253-1256`) — a window in which a concurrent agent's read returns nothing | **open**, real only under parallelism |
| #2528 | `labels --issue N` prints `#N proposed + -` with nothing after either sign when no proposal is recorded. Reads like a failure | **open**, cosmetic |
| #3251 | `sql`'s help text advertises `compilers.sort_key`, which does not exist. The working query is `SELECT tag, build_date FROM releases ORDER BY build_date` | **open**; a "list the catalog" command would stop the next agent guessing |
| #3251 | `run --args` without `--label` silently overwrites the primary capture | **already fixed in batch 005** — `triage.py:967` warns. The note is stale relative to the code |
| #2128 | Release exe layout differs: v1.4.1907's `dxc.exe` sits at the archive root, everything later at `bin/x64/`. **Read `releases.cached_path`; never construct a path** | documented behaviour, worth repeating |
| #2331 | DXC embeds your source in `!dx.source.contents`, so grepping a whole CE response for `unreachable` matches your own header comment. Grep the function body | **operator trap**, self-inflicted and worth naming |

### 15. Two verification habits worth keeping

- **`ce-verify.py` (#2528)** re-compiles the annotated source with the saved per-pane arguments
  into `manual-case-ce-panes.txt`, so link verification leaves evidence instead of a claim. Its
  natural home is `godbolt --verify`.
- **`git diff --stat <built-commit> HEAD` (#3251)** confirms the binary was built from the source
  whose line numbers you are quoting. Ten seconds; cheap insurance for any triage that cites a
  line. Here it confirmed the only differences between the built source and HEAD are inside the skill
  directory.

### 16. PowerShell silently damaged two artifacts, and three cosmetic record inconsistencies (new)

Found by reading all five records against each other, none affecting a verdict:

- **#3251's summary said "Not `-specific`" where its notes say "not `$Globals`-specific".** A
  `$`-prefixed identifier was passed to `triage.py verdict --summary` inside a **double-quoted
  PowerShell string**, so the shell expanded `$Globals` to nothing before Python ever saw it —
  silently, with no error. The mangled sentence then propagated into `overview.md`, a standing
  deliverable. **This is a real hazard on a Windows-hosted workflow**, and it is invisible: the
  text simply loses a word. #2191 shows the same sentence pattern surviving intact
  (`Not [numthreads]-specific`) because square brackets are harmless there. Corrected during
  collation from the notes, which are the source of truth; a scan of all 30 verdict summaries
  found no other instance.
- **The same shell ate a backtick escape, and that one reached a committed capture.**
  `data/issues/3251/manual-case-assert-stack.txt` lines 16 and 18 read *"the CallInst arm's
  final lse"* and *"that branch's inner lse"*. The worker wrote `` `else` ``; in a double-quoted
  PowerShell string `` `e `` is the **escape character**, so the file contains a literal
  `U+001B` followed by `lse`. **Deliberately not corrected** — hand-editing a committed capture
  is the one thing `SKILL.md` and #2128's own method notes call falsification, and the header is
  physically part of the capture file even though the damaged text is annotation rather than
  measurement. Recorded here so the next reader knows the word is "else" and knows why. Two
  other files in the batch contain `U+001B` legitimately (`2528/manual-case-ce-clang.txt`,
  `2792/manual-case-ce-panes.txt`) — those are ANSI colour codes in real captured Clang output
  and are correct as they stand.
- **Rule for both: pass any string containing `$` or a backtick to `triage.py` — or to a file —
  in single quotes.** Two different escape mechanisms, one shell, silent in both directions,
  and one of them is now permanent in the evidence.
- **#3251's `notes_path` was `data\issues\3251\notes.md`** — Windows separators and a `data/`
  prefix — where the other four use `issues/<n>/notes.md`. **Normalised during collation** with
  `triage.py verdict --notes-path`. Nothing enforces the shape, so it will recur.
- **#2128 and #2792 have no `expected_symptom`**, where #2331, #2528 and #3251 do. `reindex`'s
  completeness audit does not object, so the field is optional — but for #2792, whose whole
  finding is that a diagnostic is *missing*, a one-line statement of the expected symptom is
  exactly the field's purpose. Left as found, since editing it during collation would be putting
  words in a worker's mouth.
- **`reviewed_by` was unset on all five**, correctly — the per-issue sessions were told to leave
  it. Set to `gpt-5.6-sol` during collation, after the review actually ran.

### 17. What the independent review changed, and what was rejected

Step 10 ran on **`gpt-5.6-sol`**, briefed with the five `comment.md` paths, the `notes.md` as
background, the audience (maintainers and original reporters, public repo, threads years old),
concision as the primary criterion, and an explicit instruction to re-derive every numeral from
the evidence rather than trusting the drafts. It returned nine factual-error items and about
thirteen concision/tone items.

**Every factual claim was independently re-verified before being accepted** — `SKILL.md` warns the
reviewer can introduce errors while removing them, and that warning earned its place again: one of
its "corrections" was itself wrong (see rejections). Nine were confirmed and applied:

| draft | what was wrong | why it mattered |
| --- | --- | --- |
| #3251 | The "verbatim" `cdb` block contained a line the capture **never printed** — `File: lib\HLSL\HLOperationLower.cpp(8801)`, where `manual-case-assert-stack.txt` CASE 1 shows `File:` **blank** | **The most serious error in the batch.** A fabricated line inside a quoted block, in a draft written for the original reporter. Fixed by reproducing the capture exactly and attributing the line number to source outside the quote |
| #3251 | "on `main` and on releases back to v1.5.2010" implied a full release sweep of *stacks*; only three stack captures exist | narrowed to "on `main`, v1.5.2010 and v1.9.2607" |
| #2128 | 68,700 → 32,844 was attributed to the wrong shader — those are `corpus-large.hlsl`'s, while 0.839/0.851/0.848 are `repro.hlsl`'s | the sentence read as one shader's before-and-after when it is two shaders |
| #2128 | "the DXIL part deflates to 0.80–0.85, matching the reported band" — the measured values are 0.848 (in band) and **0.900 (above it)** | overstated the agreement with the reporter |
| #2128 | "raw sizes net out within 1.5% … so the gap is compressibility alone" — true only with the unrolled outlier included; the representative pair is **2.0× raw, 3.7× zipped** | the honest version is still a strong claim and is now the one made |
| #2128 | "compressibility did not move at all" for 0.839 → 0.851 → 0.848 | "barely moved" |
| #2128 | "zlib is reachable from exactly two places in this repo" — `ZlibCompressAppend` has two call sites, but repo-wide zlib also appears in `lib/MC/ELFObjectWriter.cpp:1025` and `lib/Support/Compression.cpp` | narrowed to the helper, which is what the claim is actually about |
| #2128 | "three people have asked for an update since" — the 2022 comment asks a different question (a PC equivalent of the Xbox macro) | "three follow-up comments (2020, 2020, 2022) went unanswered" |
| #2792 | "all 20 probed, all identical. No compiler has ever diagnosed this"; "byte-identical output" | scoped to what was measured: "in all 20 release probes back to v1.4.1907"; "identical disassembly and the same shader hash" |

**The review's real value was arithmetic, again**, and it is worth recording what it re-derived
and found **correct**: #2331's 20 release captures all exiting `2147500037`; #2528's 20
reproductions and the control's four load/store pairs; #2792's 20 exit-0 probes; #3251's
19 + 1 split, its 8+1+9+1 failure shapes and its 9 + 2 + 8 exit-status tally; and #2128's
3.74×/5.72×, 39.39% raw and 34.15% zipped, and `-Qstrip_reflect` 13.54%/8.70%.

**Rejected, with reasons.** `SKILL.md` names the classes of suggestion the reviewer reliably gets
wrong; four of the five rejections fall squarely into them.

- **#3251, "skipping asserts is not equivalent to a Release build".** Rejected as the reviewer
  being unreliable on domain specifics. `SKILL.md` documents that `gh` emulates `NDEBUG` so a
  Debug binary can reproduce a Release symptom, and 19 independent release probes corroborate the
  prediction. Accepting this would have deleted a correct, load-bearing claim.
- **#2331, "remove imagined-reader rhetoric from the stale-text finding".** Partially rejected.
  The clause the reviewer wanted gone — *"someone spot-checking them today could reasonably
  conclude the whole report is obsolete. It is not"* — **is** the point of a `text_stale` finding.
  `SKILL.md` warns the reviewer cuts actionable caveats and reads caveats aimed at future triagers
  as accusations. Shortened, not removed.
- **#2331, "condense the Clang comparison".** Partially rejected: the proposed replacement dropped
  both the #1702-style control (Clang also fails on inputs DXC accepts) and the @llvm-beanz
  addressee, which is the paragraph's entire reason to exist. Compressed by hand instead, keeping
  both.
- **#2792, "remove implementation-design speculation".** Partially rejected. That
  `PSVResourceBindInfo0` carries no size is **measured**
  (`DxilPipelineStateValidation.h:240`) and is the actionable half of the paragraph. Kept the
  mechanism, softened to "it cannot make this comparison from the data it reads today", and
  dropped the unmeasurable half — the claim that a front-end fix "needs no format change" was an
  effort estimate, which is not this skill's to make.
- **#2792, the "I may be missing history" label hedge.** The reviewer proposed dropping it as
  house-style boilerplate; applied to #2128 and #2528, **rejected for #2792**, which proposes
  *removing* the `bug` label. `SKILL.md` step 8 requires the hedge specifically for removals.

**One reviewer suggestion was accepted that is worth naming separately**, because it is the class
`SKILL.md` says to accept without argument: #2528's claim that the `SV_Position` framing
"understates" the defect was an editorial judgement about the reporter, and its assertion that the
silent case "is the common case" had **no measurement behind it at all**. The first was
reframed; the second was **deleted**.

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


### Draft — [#2128](https://github.com/microsoft/DirectXShaderCompiler/issues/2128) Generated bytecode by dxc has very higher compression ratio

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2128](https://github.com/microsoft/DirectXShaderCompiler/issues/2128).

**Still reproduces on `main` (1.9.0.5433, `13730886e`), and the original report's numbers hold to
within a few points.**

Compiled three pixel shaders with both compilers (`dxc -T ps_6_0 -E main -O3`,
`fxc /T ps_5_1 /E main /O3`) and deflated each object the way a `.zip` member is compressed.
Totals below are the two representative shaders; the third is a 32×-unrolled outlier that
flatters both compilers and is broken out under Method:

| | raw | zipped | ratio | reported in 2019 |
| --- | --- | --- | --- | --- |
| fxc | 5516 | 1825 | **0.33** | ~0.30 |
| dxc | 11152 | 6833 | 0.61 | — |
| dxc `-Qstrip_reflect` | 6992 | 5389 | **0.77** | 0.80–0.85 |

Zipped, dxc is **3.7× larger** for the same shaders — the reported ~3×. Measured alone, the DXIL
part deflates to `0.848` on the mid-size shader, inside the reported 0.80–0.85 band, and `0.900`
on the small one, just above it. fxc's `SHEX` chunk for that mid-size shader deflates to `0.271`.

The two containers encode code differently: DXIL is LLVM 3.7 bitcode (`docs/DXIL.rst:151`),
bit-packed VBR with abbreviations, where DXBC's `SHEX` is byte-aligned 32-bit tokens with heavy
repetition. Raw size is the smaller factor — on the two representative shaders dxc is 2.0× fxc
raw against 3.7× zipped, and on the 32×-unrolled shader dxc is *smaller* raw (35,364 vs 41,708
bytes). That is the shape @Division described in 2022.

**Half of @BitMD's 2019 comment was delivered.** Between v1.4.1907 and v1.5.2010 the reflection
metadata moved out of the module into a separate `STAT` part
(`DxilContainerAssembler.cpp:2085-2115`): the large shader's DXIL part went 68,700 → 32,844
bytes, and corpus size fell 39% raw / 34% zipped. Compressibility barely moved — the mid-size
shader's DXIL part deflates to `0.839` at v1.4.1907, `0.851` at v1.5.2010 and `0.848` today, and
across all 20 releases to v1.9.2607 the corpus ratio stays between 0.523 and 0.568.

**@Division — there is no PC equivalent of `__XBOX_DISABLE_SHADER_OBJECT_COMPRESSION`, and
nothing to disable.** DXC's compression helper `ZlibCompressAppend` has exactly two call sites,
and neither touches the shader object: the PDB writer
(`lib/DxilPdbInfo/DxilPdbInfoWriter.cpp:31`) and the `SRCI` embedded-source part
(`tools/clang/tools/dxcompiler/dxcshadersourceinfo.cpp:425`). `DxilContainerAssembler` writes
every part uncompressed; the density you measured is the bitcode encoding itself.

What is available is `-Qstrip_reflect` (also `-Qstrip_debug`, `-Qstrip_rootsignature`,
`-Qstrip_priv`, `-Qstrip_reflect_from_dxil`). Worth 13.5% raw and 8.7% zipped here — real, but
it does not close a 3.7× gap, which is what @BitMD said in 2019.

One caveat for re-measuring: `STAT` is a clone of the module, so whole-container deflate
deduplicates it against `DXIL`. The *ratio* improves while the zipped byte count gets worse —
the small shader zips to 2,393 bytes today versus 2,106 at v1.4.1907. For a fixed shader set,
compare zipped bytes, not ratios.

**Suggested labels:** add `fxc-disagrees` (a measured fxc/dxc difference) and `enhancement` (the
emitted code is correct; the ask is a different container encoding, not a bug fix). `dxil` and
`revisit-sooner` both still fit.

Three follow-up comments (2020, 2020, 2022) went unanswered. Whether to change the container
encoding is a product decision; a stated position, even "no change planned", would close out a
seven-year-old question.

<details>
<summary>Method — repeatable</summary>

Corpus is agent-constructed; the issue contains no code. Ratio is
`len(raw_deflate(bytes)) / len(bytes)` at level 9 (`wbits=-15`), i.e. a `.zip` member, and a
`.zip` compresses members independently. Containers are split using
`DxilContainerHeader`/`DxilPartHeader` from `include/dxc/DxilContainer/DxilContainer.h`; DXIL
reuses the DXBC container format, so the per-part figures are directly comparable. fxc is
10.0.26100.0 from the Windows SDK. The harness pins both ends of the scale on every run — 4 KiB
of sha256-chain bytes must measure ≥ 0.98 (got 1.001) and HLSL source text ≤ 0.50 (got 0.398).

The table above excludes a third, 32×-unrolled shader: 32 near-identical blocks flatter both
compilers (fxc reaches 0.059 on it) and it is not representative. Including it the zipped
multiple is 5.72×, not 3.7×.

</details>

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#2331](https://github.com/microsoft/DirectXShaderCompiler/issues/2331) Problem with DXIL signing and switch case/enum use

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2331](https://github.com/microsoft/DirectXShaderCompiler/issues/2331).

**Still reproduces on `main` (1.9.0.5433, `13730886e`).**

```
$ dxc -T ps_6_0 -E MainPS repro.hlsl
error: validation errors
repro.hlsl:24:1: error: Instructions must be of an allowed type.
note: at 'unreachable' in block '#4' of function 'MainPS'.
Validation failed.
```

Compiler Explorer, unmodified body repro: **https://godbolt.org/z/nEqsn9nEW**

@tristanlabelle's 2019 diagnosis still holds: `-Vd` shows the fall-off path becoming
`unreachable`. `utils/hct/hctdb.py` marks `Unreachable` disallowed in
`mark_disallowed_operations`; the generated `IsLLVMInstructionAllowed()` is checked in
`lib/DxilValidation/DxilValidation.cpp` before `ValidationRule::InstrAllowed` is emitted.

**Signing is not involved.** The report's `DXIL.dll not found` warning is environmental
(shader-playground shipped no `dxil.dll`); validation runs either way and fails here, so nothing
reaches signing. Since the external validation paths were removed from `dxcompiler.dll`, current
builds do not consult a sibling `dxil.dll` at all, and valid containers are signed without one.

**Two claims in the body no longer describe the compiler** — worth knowing, because someone
spot-checking them today could reasonably conclude the whole report is obsolete. It is not; only
these two have moved:

| body claim | today |
| --- | --- |
| comment out one `case` → "validates clean, but it shouldn't" | `error: control may reach end of non-void function [-Wreturn-type]` — the validator is never reached |
| add a fourth enumerator `Fake` → still a validation error | same front-end error |

Adding `default:` still compiles clean, as the body says.

Measured across all 20 releases from v1.4.1907: both changed between **v1.4.1907 and
v1.5.2010**. In source, `warn_maybe_falloff_nonvoid_function` gained `DefaultError` in
`8c43a1456`, *"Default to error on missing return from non-void function"* — in v1.5.2010,
not in v1.4.1907. (434 commits in that window, so: strong attribution, not a bisected one.)

That is the fourth bullet of tristanlabelle's list, delivered in 2020 — but only where the
front end can see the switch is non-exhaustive. **A switch covering every declared enumerator
still satisfies `-Wswitch`, passes Sema, and lands on the validator**, which is the whole of
what remains here. The repro's own `(::QualityT)(shaderKey & 3)` can yield `3`, so the
fall-off-the-end path is reachable — the point tristanlabelle made when he argued a
`default:` on an exhaustive enum switch is legitimate rather than redundant.

His first bullet has also largely been addressed: the error now carries a source location and
names the instruction, where in 2019 it printed only `at 0x24f9e5b2a10 inside block #0`.

On @llvm-beanz's 2024 note about removing these instructions during DXIL lowering in Clang:
clang cannot compile this shader as written, and a compute translation of it hits a backend
error that clang also produces for inputs DXC accepts, so neither says anything here. On a
cut-down restating of the construct, clang compiles it and emits no `unreachable` — the default
edge goes to the merge block and the undefined path contributes `poison` to the phis.

Nothing here disturbs the 2024 position that this won't be fixed in DXC; whether "dormant"
should mean closed is a call for the team.

**Suggested labels:** add `validation` ("Related to validation or signing" — this is a DXIL
validation failure) and `incorrect-code` (the shader is incorrect, and the complaint is that DXC
catches it in the validator rather than in Sema). Keep `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#2528](https://github.com/microsoft/DirectXShaderCompiler/issues/2528) Remainder of inout signature element not passed through when one component is modified

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2528](https://github.com/microsoft/DirectXShaderCompiler/issues/2528).

Still reproduces on `main` (`1.9.0.5433`, `13730886e`), and on all 20 releases from
v1.4.1907 (2019-07) to v1.9.2607 — the whole checkable range, which starts before this was
filed. The repro in the body works as written.

**Compiler Explorer:** https://godbolt.org/z/EaYncchW3 (FXC, DXC 1.6.2112, DXC trunk; the
banner says which pane shows what).

`dxc -T vs_6_0 -E main` on the shader in the body:

```
error: validation errors

repro.hlsl:10: error: Not all elements of output SV_Position were written.
repro.hlsl:10: error: Not all elements of SV_Position were written.
Validation failed.
```

Adding `-Vd` shows the module behind that error:

```
; Output signature:
;
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; SV_Position              0   xyzw        0      POS   float      w

define void @main() {
  call void @dx.op.storeOutput.f32(i32 5, i32 0, i32 0, i8 3, float 1.000000e+00)  ; StoreOutput(outputSigId,rowIndex,colIndex,value)
  ret void
}
```

One `storeOutput`, and no `loadInput` at all — `x`, `y` and `z` are neither read nor written.
Empty the body and the same shader emits four `loadInput`/`storeOutput` pairs, so writing one
component is what suppresses the rest. FXC on the identical file at `/T vs_5_0` gives
`mov o0.xyz, v0.xyzx` / `mov o0.w, l(1.000000)`, with `Used = xyzw`.

### On the impact question

Re: [the 2024 note](https://github.com/microsoft/DirectXShaderCompiler/issues/2528#issuecomment-2176615654)
about real-life scenarios — `SV_Position` makes this loud, because that element *must* be fully
written, so the validator catches it and you get a compile error. On an ordinary varying there is
no such rule, and the same omission exits 0 with no diagnostic:

```hlsl
struct V { float4 pos : SV_Position; float4 uv : TEXCOORD0; };
void main(inout V v) { v.uv.x = 1; }
```

`dxc -T vs_6_0 -E main` **exits 0**, no diagnostic, validation passes:

```
; Output signature:
;
; Name                 Index   Mask Register SysValue  Format   Used
; -------------------- ----- ------ -------- -------- ------- ------
; SV_Position              0   xyzw        0      POS   float   xyzw
; TEXCOORD                 0   xyzw        1     NONE   float   x

  call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 0, float 1.000000e+00)  ; StoreOutput(outputSigId,rowIndex,colIndex,value)
```

`TEXCOORD0` is declared `xyzw` but only `.x` is written, so `.yzw` reach the consumer
undefined. FXC emits `mov o1.x, l(1.000000)` / `mov o1.yzw, v1.yyzw`. This shape reproduces on
v1.4.1907 too.

### Labels

Suggest adding **`correctness`** — the varying case emits a shader with undefined output
components and no diagnostic. Keep `bug` and `fxc-disagrees`: FXC and DXC were run on the same
files and agree on all three controls, differing only on the two partial-write cases.

**`check-in-clang`** is currently unanswerable: `hlsl_clang_trunk` rejects
`inout float4 pos : SV_Position` with `attribute 'SV_Position' only applies to a field or
parameter of type 'float/float1/float2/float3/float4'`, and that same error fires on the
known-good empty-body control. Worth re-checking once Clang supports `inout` semantic
parameters.

No removals.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#2792](https://github.com/microsoft/DirectXShaderCompiler/issues/2792) Need to report error when use constant which has offset bigger than root constant size.

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2792](https://github.com/microsoft/DirectXShaderCompiler/issues/2792).

Still reproduces on `main` (1.9.0.5433, `13730886e`) and in all 20 release probes back to
v1.4.1907. Every probe exits 0 and codegens the out-of-bounds read; none diagnoses it.

The repro from the description compiles clean, exit 0, no diagnostic:

```
;   } cb;                                             ; Offset:    0 Size:     8
  %2 = call %dx.types.CBufRet.f32 @dx.op.cbufferLoadLegacy.f32(i32 59, %dx.types.Handle %1, i32 0)  ; CBufferLoadLegacy(handle,regIndex)
  %3 = extractvalue %dx.types.CBufRet.f32 %2, 1
```

The cbuffer is 8 bytes, the root constant block reserves 4, and `extractvalue …, 1`
is the read of the word past the end.

Compiler Explorer, all three panes agreeing: **https://godbolt.org/z/d5zcrTPjP**
(restated as a compute shader so `hlsl_clang_trunk` can lower it; the pixel form
behaves the same in DXC).

**No validator compares `num32BitConstants` against the cbuffer size.** Changing it
from `1` to `2` — making the shader entirely correct — produces identical
disassembly and the same shader hash. In `DxilRootSignatureValidator.cpp` a root
constant block is registered as a CBV range of one register and `Num32BitValues`
is not passed in; the field is parsed, serialised and printed, but no validator
reads it.

Nearby checking does run, so this is a gap in it rather than its absence — binding
`b1` while the cbuffer sits at `b0` is rejected:

```
error: Shader CBV descriptor range (RegisterSpace=0, NumDescriptors=1, BaseShaderRegister=0) is not fully bound in root signature.
```

That check is `VerifyRootSignatureWithShaderPSV`, which reads PSV bind info
(`ResType, Space, LowerBound, UpperBound`) — no cbuffer size is carried there, so
it cannot make this comparison from the data it reads today. The front end has
both the `[RootSignature(...)]` string and the cbuffer layout in hand. Which
should own the check is a design call.

`hlsl_clang_trunk` does not diagnose it either, but that is weak evidence: it
also accepts the `b1`/`b0` mismatch above, so its silence is "not implemented
there either" rather than an independent judgement.

**Labels:** suggest adding `diagnostic`, `enhancement` and `check-in-clang`. Since
no probed release has this check and nothing regressed, `bug` may be worth
dropping — though the neighbouring case being an error makes "oversight" a fair
reading too. That removal is a suggestion; I may be missing history behind the
label. Whether the right diagnostic is an error or a warning, and whether the
D3D12 spec makes this invalid or undefined, are product decisions and not
something this triage measured.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

### Draft — [#3251](https://github.com/microsoft/DirectXShaderCompiler/issues/3251) Missing implementation for HLOpcodeGroup::NotHL in TranslateCBAddressUserLegacy

````markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3251](https://github.com/microsoft/DirectXShaderCompiler/issues/3251).

**Still reproduces on `main` (1.9.0.5433, `13730886e`), and on every release binary that supports
`as_6_5`.** The repro in the body works as filed; the assert is still the one named in the title,
still in `TranslateCBAddressUserLegacy`, still because the user is `HLOpcodeGroup::NotHL`.

```
$ dxc -T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug repro.hlsl
Internal compiler error: Terminal Error 0x80000003
```

That is all a plain run prints — the assert text goes to `OutputDebugString`. Under `cdb`:

```
Error:  !(0)
File:
Func:   `anonymous-namespace'::TranslateCBAddressUserLegacy.
        not implemented yet
```

(cdb leaves `File:` empty; in current source that `DXASSERT(0, "not implemented yet")` is
`lib/HLSL/HLOperationLower.cpp:8801`.) The stack reaches it as
`DxilGenerationPass::GenerateDxilOperations` → `TranslateHLSubscript`
(`CBufferSubscript`) → `TranslateCBOperationsLegacy` → `TranslateCBAddressUserLegacy`.

The line moved since the report. `HLOperationLower.cpp:6207` was then the `CallInst` arm's final
`else`. PR #3034 (`eaa7f95d0`, six days after this was filed) added an `IntrinsicInst` branch for
lifetime markers above it, and `llvm.memcpy` *is* an `IntrinsicInst`, so it now lands in that
branch's inner `else` at 8801 — textually identical to the outer one, now at 8804.

### The assert is not the whole defect

Every shipping release is a Release build, where `DXASSERT` is `do { } while (0)` — so it would
be easy to read "no release asserts" as "fixed". It is not. With the assert compiled out the
memcpy is left untranslated *and unerased*, and the pointer it uses is deleted anyway
(`BCI->eraseFromParent()` at 8845; `DXASSERT(CI->use_empty(), …); CI->eraseFromParent();` at
9920–9922, that guard also compiled out). LLVM's backstop
`assert(use_empty() && "Uses remain when a value is destroyed!")` is compiled out too. Continuing
past both asserts in a debugger — which runs what a release build runs — ends in an access
violation in `InstCombiner::visitCallInst` → `MemTransferInst::getSource`, dereferencing the
dangling operand.

So the release history is a real measurement, and it is uniform: **all 19 releases from
v1.5.2010 (2020-10) to v1.9.2607 fail.** v1.4.1907 is the only exception and it never ran the
repro — `error: invalid profile as_6_5`, confirmed with a minimal `DispatchMesh` shader. Since
v1.5.2010 predates this report by three weeks, that covers the issue's whole life.

The failure wears four different faces across those releases, which is worth knowing for anyone
matching on output: `Internal compiler error: access violation` (8), no output at all (1,
v1.5.2010), `DataLayout::getTypeSizeInBits(): Unsupported type` (9, split between
`DXC_E_LLVM_UNREACHABLE` and E_FAIL), and `llvm::cast<X>() argument of incompatible type!` (1,
v1.8.2403). Eight of the 19 exit with plain E_FAIL — the same status as a syntax error.

Compiler Explorer: **https://godbolt.org/z/arjrMWhWf** — `dxc_1_6_2112` and `dxc_trunk`, both
`SIGSEGV`. CE builds are Release, so the assert itself cannot appear there; the page shows the
post-`NDEBUG` consequence, and it corroborates the Debug build rather than standing in for it.

### Scope, and a workaround

Measured on `main`:

- **Not `$Globals`-specific.** Moving the global into an explicit `cbuffer MyCB : register(b0)`
  traps identically.
- **Not any memcpy out of a cbuffer.** The same whole-struct copy out of the cbuffer into an
  `RWStructuredBuffer` element in `cs_6_0` compiles cleanly (exit 0) — on the tested cases it is
  the `DispatchMesh` payload that keeps the copy as an `llvm.memcpy` into DXIL lowering.
- **Writing the copy field by field compiles cleanly** — on `main`, v1.5.2010 and v1.9.2607.
  That is a usable workaround today:

  ```hlsl
  p.lhSampleData.linearTerms[0] = g_lhSampleData.linearTerms[0];
  // ... etc, one field at a time
  ```

Labels: `bug` + `crash` are already right; no change suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
````

---

## Caveats

- **Sampling is deliberately unrepresentative, and this is the batch where it shows most.**
  Selection is **oldest-first**: four of the five were filed in 2019–2020, and the fifth in
  2020-11. All five reproduce and all five always have. **Do not read that as a statement about
  the backlog** — it is a statement about issues old enough to have survived six years without
  anyone fixing them, which is a population selected for being hard, low-priority or both. A
  random sample would be expected to contain issues that are fixed, unreproducible, or
  duplicates; this one contains none by construction.
- **Two of the five were additionally chosen to stress specific tooling** (#2792 for the
  `invalid-probe` classifier, #2331 for DXIL signing), which biases the method findings toward
  those areas — but note both stress tests came back *negative* on the thing they were aimed at,
  and the defects found were found by workers going looking beyond their brief.
- **The review gate was suspended.** See the callout at the top. This report's own judgement is
  that quality did not slip, but that judgement is made by the same run it is judging.
- **#2128's repro is `agent-constructed`.** The issue supplies no shader. Its corpus, its
  measurement rule and its script were all written during triage, and the corpus was found to
  bias the result once and was corrected in the open. The reporter's original shaders are not
  available, so agreement with their 2019 numbers is agreement in *magnitude*, not a
  reproduction.
- **#2128's `-Qstrip_reflect` ratio (0.771) is below the reporter's stated 0.80–0.85**, and its
  overall multiple (3.7×) is above their ~3×. Both columns are shown in the draft rather than
  averaged into a claim of exact agreement.
- **#2331's FXC-era history stops at v1.4.1907**, which is the bisection floor. "Always
  reproduced" means "for as long as it is possible to check" for #2128, #2331, #2528 and #2792
  alike; all four predate the floor. For #3251 the effective floor is v1.5.2010, the first
  release with `as_6_5`, which is nonetheless three weeks older than the report.
- **#2331's stale-text attribution to `8c43a1456` is a 434-commit window, not a bisected
  commit.** The behaviour change is dated to between v1.4.1907 and v1.5.2010 by measurement; the
  commit within that window is inferred from source.
- **#3251's release-build claim rests on `NDEBUG` emulation under `cdb` plus 19 release probes**,
  not on a Release build with asserts enabled — those do not ship. The mechanism is cited so the
  reasoning can be checked.
- **#3251's third defect (`onlyUsedByLifetimeMarkers`) is not triaged.** It surfaced from a
  discarded control, has a captured stack, and nobody has checked whether an issue exists for it.
- **No `--repeat` hit rate is quoted anywhere in this batch.** All five repros are deterministic,
  so `SKILL.md` step 5's rule is satisfied vacuously.
- **`triage.py` and `SKILL.md` were changed during collation.** `_has_positive_clause` plus a
  capture-time warning and eight tests; `SKILL.md`'s absence-guard paragraph corrected, the `cdb`
  recipe extended, and Clang's vertex-stage limitation added. **No verdict, capture, command line
  or exit status was altered by any of it** — the warning is `stderr`-only and changes no stored
  data. `reindex` was run once, at the start of collation, before any edit.
- **Two fields on #3251's `verdict.json` were corrected during collation**: `notes_path`
  normalised to the shape the other four use, and a `$Globals` that PowerShell had expanded away
  restored from `notes.md`. Neither is a conclusion; no measurement, verdict or capture was
  touched.
- **`overview.md` is generated and was regenerated last**, after `reviewed_by` was set on all
  five, because `audit`'s staleness gate compares it against the newest `verdict.json`.

## Suggested next step

1. **Adopt #3251 as a regression fixture for `internal_failure`** (method note 13). One defect
   with four text signatures and three exit statuses across 19 releases, eight of which are
   status-indistinguishable from a syntax error, is better evidence than any synthetic string in
   `test_predicates.py` today.
2. **Check whether the `onlyUsedByLifetimeMarkers` trap is a known issue.** #3251's discarded
   control found it, the stack is captured, and nobody has looked. If it is unreported, filing it
   is a straightforward win — but filing is a human action, not this workflow's.
3. **Compose batch 007 with at least one issue that does *not* reproduce.** Six batches in, the
   verdict distribution is 27 `repros` against 3 anything-else. Either the backlog really is that
   solid, or the selection has never given the workflow a chance to say "fixed" — and #3768 is
   the only time it has. Deliberately including an issue whose thread claims a fix would test the
   `does-not-repro` path, which is currently the least exercised in the skill.
4. **Give one worker no hazard brief at all.** Carried forward from batch 005, still untested.
   Batch 006 reinforces the question rather than answering it: #2792's worker was told exactly
   what to stress, found that thing to be fine, and then found two real defects *elsewhere* in
   the same code. That is consistent with briefs anchoring attention as much as directing it.
5. **Give `match.json` a way to record a measured fact about an output file** (method note 5), or
   decide deliberately that it will not have one. Signing, container structure, part sizes and
   hashes are all currently prose, invisible to `audit` and to every cross-batch query. #2128
   shows the workaround (a committed script plus a captured run) works; it just is not indexed.
