# Batch 010 — orchestrator notes

Written by the orchestrating session for the **fresh collation session**, which by design never
sees the orchestrator's conversation. Everything collation needs that is not already in an
issue directory must be here.

Batch 010 issues: **2604, 3686, 3708, 3726, 3811**.

---

## 1. Ground-truth provenance was wrong for batches 006–009 — fixed for 010, NOT yet fixed for 006–009

This is the most important thing in this file, and it needs a decision from the maintainer.

### What happened

The ground-truth Debug binary was **rebuilt on 2026-08-06 20:07**, part-way through the pass.
The compiler registry (`.cache/compilers/main-debug.json`) was never updated, so it kept
reporting the *previous* build. Nobody noticed because `triage.py` records the compiler **id**
and **exe path** in every capture header — it does not record the compiler's **commit**:

```
# compiler: main-debug
# exe: <repo>/build/Debug/bin/dxc.exe      <-- a path, not an identity
```

`main-debug` is therefore a **mutable label**. "Triaged against main-debug" means different
compilers in different batches, and nothing on disk says which.

### What was actually damaged — and what was not

Measured across all 45 triaged issues, comparing each issue's `triaged_with_commit` against the
version string DXC embeds in its own DXIL output (`!0 = !{!"dxc(private) ..."}`):

- **Zero mismatches.** Every issue's recorded commit agrees with the version embedded in its own
  captures. Batches 001–005 record `eff900d5`; batches 006–009 record `ab5400907`. The workers
  read the live `--version` rather than the stale registry, so **no verdict is misattributed**.

So the verdicts are sound. The problem is narrower, and worse in a different way:

### The real defect: `ab5400907` resolves nowhere

`ab5400907` is a **fork-local merge commit that was orphaned by the commit-message history
rewrite**. It is now reachable only from two local backup refs
(`refs/heads/triage-backup-pre-rewrite`, `refs/original/refs/heads/triage`). It is not on
`origin/triage`, not on `upstream/main`, and will not resolve for any reader.

**25 `comment.md` drafts — text intended to be posted publicly on other people's issues — cite
it as the ground truth.** A maintainer posting those would be telling reporters "still
reproduces on main (ab5400907)" where that commit cannot be looked up.

### The correct anchor

`ab5400907` is a merge of the triage branch into **upstream main `13730886e`**
("Improve Copilot release note review guidance (#8733)", 2026-08-06). Verified:

```
git diff --name-only 13730886e ab5400907 -- . ':(exclude).github/skills/dxc-issue-triage'
  -> no output
# positive control, same command vs the older build:
git diff --name-only eff900d5   ab5400907 -- . ':(exclude).github/skills/dxc-issue-triage'
  -> 32 files
```

The triage branch adds **nothing outside the skill directory**, so the ground-truth binary is a
build of upstream main at `13730886e`. That commit **is** on `upstream/main` and resolves for
anyone. `eff900d5` (batches 001–005) is likewise on `upstream/main` and is fine as-is.

### What has been done

- The registry (DB + `main-debug.json`, both gitignored) now records `13730886e`, with a
  `provenance_note` explaining the discrepancy against the binary's self-reported string.
- **Batch 010 workers were briefed to cite `13730886e`** and explicitly told not to cite
  `ab5400907`. Batch 010 should be correct on arrival.

### What has NOT been done — decision required

The orphaned SHA still appears in **184 committed files**. It splits cleanly:

| Category | Files | Action |
| --- | ---: | --- |
| **Captured compiler output** | 83 | **Do not touch.** The SHA is what the binary printed. Rewriting it would falsify evidence. |
| `comment.md` (publicly postable) | 25 | Should be corrected to `13730886e` |
| `notes.md` | 25 | Should be corrected |
| `verdict.json` (`triaged_with_commit`) | 25 | Should be corrected |
| reports (`batch-00N.md`, `overview.md`) | 11 | Should be corrected |
| misc (`expected.md`, `method-notes.md`, `match*.json`, …) | 15 | Review individually |

This rewrites already-committed evidence across four batches, so it was **flagged rather than
applied unilaterally**. It is trivially revertable as its own commit. Recommended as a separate,
clearly-labelled change — not folded into batch 010.

### The durable fix, for SKILL.md

Two changes, both structural rather than "remember to check":

1. **Capture headers must record the compiler's commit, not just its id and path.** An
   identity that lives only in a mutable side-table is not provenance. Had the header carried
   the commit, the rebuild would have been visible in the first capture after it.
2. **`triage.py compiler` re-registration updates the DB but not `main-debug.json`.** That
   silent divergence is exactly how the registry went stale. Either write both or stop writing
   the JSON.

Also worth stating explicitly: **cite a commit a reader can resolve.** A fork-local or rewritten
SHA in a public comment is worse than no SHA, because it looks checkable and is not.

---

## 2. Why these five issues, and what each is testing

Chosen to hit two axes the previous nine batches never touched.

| # | Age / labels | Why chosen |
| --- | --- | --- |
| **2604** | 2019-11, `enhancement` | Oldest untriaged. About the **compiler API**, not `dxc.exe` — a different code path, which is the issue's whole point. Tests whether the harness pattern proven on 3237 generalises. |
| **3686** | 2021-04, `build`, `macos` | **New axis:** answerable from **release/CI metadata**, not by running the compiler. SKILL.md is under-specified for this shape. 12 comments, so the thread may already contain a decision. |
| **3708** | 2021-04, `fxc-disagrees` | Complete minimal repro (`int array[(10).x]`). Three-way FXC/DXC/Clang comparison; possible language-design call rather than a bug. |
| **3726** | 2021-04, `incorrect-code` | Missing **front-end** diagnostic (backend catches it, Sema does not). Strong Clang-pane candidate; also has an explicit SPIR-V dimension. |
| **3811** | 2021-06, `validation`, 0 comments | Uninitialised value → `undef` with no diagnostic. Carries its own control (the straight-line case that *does* error). |

### A deliberate blind duplicate test — do not skip this

**3811 was chosen partly because it may overlap with issues already triaged in earlier batches.**
Its worker was told nothing about any other issue, exactly as 2188/2191 were handled in batch
004. Independent convergence is far stronger evidence of duplication than one agent noticing two
similar titles.

**Collation must check this explicitly.** Compare 3811 against the previously triaged
uninitialised-value / undef issues in `data/issues/` and decide whether any are duplicates,
partial duplicates, or genuinely distinct (e.g. differing by control flow, optimisation level,
or which component should diagnose). Do not assume similarity implies duplication — a
`duplicate-of #N` suggested action needs the same evidence bar as any other verdict.

---

## 3. Standing hazards the workers were briefed on

Repeated here because collation should verify they were respected.

- **The agent `grep` tool silently returns "no matches found", with no error, when no `glob`
  filter is passed.** Measured 7/7 false zeroes in this tree; 4/4 accurate with a glob. Any
  *absence* check run through it yields a confident false clean. Use `Select-String` or
  `git grep` wherever a zero result is load-bearing. Already recorded in SKILL.md.
- **Validate absence-check patterns against a known-positive before trusting a clean result.**
  Backslash escaping differs between JSON (`C:\\prj`) and plain text (`C:\prj`) and has bitten
  in both directions.
- **No absolute machine paths in committed artifacts.** `triage.py` redacts only what it writes;
  hand-written and harness-written files bypass `display_exe`. Roughly **27 files across batches
  001–008 still carry absolute paths** — a second pending decision, independent of the SHA one.
  `redact_paths.py` is written and ready; it deliberately excludes executables (tokenising a path
  inside a `.py`/`.cmd` makes it non-runnable, not portable) and `3237/method-notes.md` (which
  quotes both path forms as its own evidence).
- **`triage.py reindex` was withdrawn from all worker briefs** — its `--reset` defaults to true,
  so it wipes shared tables and would destroy other workers' in-flight rows. Collation runs the
  one authoritative reindex.

---

## 4. Collation checklist

1. **Run `reindex` once** — before anything else. It re-scores every archived probe with today's
   predicate code and flags stale evidence and completeness gaps. It is a regression test, not a
   restore.
2. **Check the 3811 duplicate question** against earlier undef/uninitialised-value issues.
3. **Verify no worker escaped its boundary**: `git status` should show changes only under
   `data/issues/{2604,3686,3708,3726,3811}/` plus report files. Nothing in `scripts/`, nothing
   in `SKILL.md`, nothing in another issue's directory, no DXC source.
4. **Confirm every issue cites `13730886e`** and none cites `ab5400907`. Batch 010 has no excuse
   for the old SHA.
5. **Run the step-10 independent draft review on a different model.** Apply with judgement:
   it is reliably right about verbosity and unsupported claims, unreliable about domain
   specifics, and it will try to paraphrase away literal diagnostic text that people search for.
6. **Check 3686's shape.** If it landed as `not-compiler-verifiable`, make sure its evidence is
   still on disk and re-checkable — that status has previously been used as cover for claims
   nobody wrote down.
7. Promote `method-notes.md` findings into SKILL.md; write `reports/batch-010.md`; regenerate
   `overview.md`; splice drafts with `render_comments.py`.
8. **Never write `#NNNN`, `GH-NNNN` or an issue/PR URL in a commit message** — bare numbers only.
   A tagged commit message posts a cross-reference onto the issue, which this workflow must not
   do. Scan the message with a pattern validated against a known-positive before committing.

---

## 5. Orchestrator verification log

Independent re-checks of each worker's load-bearing claims, run by the orchestrator against the
repo and GitHub rather than accepted from the report.

### 3686 — verified, and the worker was stricter than my check

| Claim | Verdict |
| --- | --- |
| 0 macOS assets across every release | **Confirmed.** My own census found 0, with a classifier positive control (3/3 synthetic macOS names correctly matched). |
| Linux first shipped at v1.7.2212 | **Confirmed** — `linux_dxc_2022_12_16.tar.gz`, earliest Linux asset. |
| macOS is built and tested but publishes no artifact | **Confirmed** in `azure-pipelines.yml`: `MacOS_Clang_Release`/`Debug` at L148-156 run on `$(image)` = `macOS-latest`; the only `PublishPipelineArtifact@1` is at L106 in the Windows job (`windows-2022`, L29). macOS reaches only `PublishTestResults@2` (L208). |

**My spot-check was wrong where it differed.** I counted 27 releases / 76 assets / 19 Linux
against the worker's 26 / 73 / 18. The difference is a single **unpublished draft release**
(empty `tagName`, `isDraft=true`, `publishedAt=0001-01-01`) carrying 3 assets, one of them Linux.
The worker was correct to exclude it — a draft is not a published artifact. Worth noting that
**even including the draft there are still zero macOS assets**, so the finding survives either
counting rule. The published numbers in the draft comment (26 tags, 73 assets) are right.

Lesson: `gh release list` returns drafts. State the population being counted ("published
releases") rather than "all releases", or a reader re-running the query gets different totals.

### Real bug in shared tooling — `triage.py` cannot fetch non-cp1252 threads

Reported by the 3686 worker and **confirmed at `scripts/triage.py:235`**:

```python
def gh(*args):
    return subprocess.check_output(["gh", *args], text=True, ...)
```

There is **no `encoding=` argument**. With `text=True`, Python falls back to
`locale.getpreferredencoding()` — cp1252 on this machine — so `fetch` dies with
`UnicodeDecodeError` on any issue thread containing an emoji or other non-Latin-1 text.
Compare line 224 and the other file opens, which all pass `encoding="utf-8"` explicitly; the
subprocess call is the one place that does not.

- **Workaround** used by the worker: `$env:PYTHONUTF8='1'`.
- **Fix:** add `encoding="utf-8"` to the `check_output` call (and check the sibling
  `subprocess.run` calls at 689 and 1059, which have the same shape).
- **Deliberately not applied mid-batch** — `scripts/` is shared state and four workers were
  still running. Apply at collation, and check whether other batch-010 workers hit it
  independently.

This is a silent-failure class the workflow keeps rediscovering: the failure is loud when it
happens, but it selects *which issues can be triaged at all*, so a whole category of threads
would quietly never make it into a batch.

### 3811 — verified; the reporter's 2021 guess was literally the code

| Claim | Verdict |
| --- | --- |
| Validator exempts PHI nodes by name | **Confirmed** at `lib/DxilValidation/DxilValidation.cpp:3601`: `bool LegalUndef = isa<PHINode>(&I);`, inside `for (Value *op : I.operands()) { if (isa<UndefValue>(op)) {`. The rule is local and syntactic. |
| Silence ended at v1.7.2308 | **Confirmed precisely.** `1380cf88e` = "Add diagnostics for uninitialized `out` parameters (#5047)", 2023-03-01. It is an ancestor of `v1.7.2308` and **not** of `v1.7.2212` — a clean, checkable boundary rather than an inferred one. |
| `-Wparameter-usage` exists | **Confirmed**: `DiagnosticGroups.td:805`, `def HLSLParameterUsage : DiagGroup<"parameter-usage">`. |
| CE link `57zn3j6YK` | **HTTP 200.** |

The reporter wrote in 2021 that this happens "because undef is permitted in phi nodes, it seems".
That hypothesis is the source line, verbatim. Worth saying so in the draft — it is unusually
strong corroboration and it tells the maintainer the fix location is already known.

**The `text_stale` flag is the important part.** The title says "no error/warning", and that half
is now false for the reported `out`-parameter shape — so a maintainer spot-checking the title
would reasonably conclude "cannot reproduce" and close a live defect. The worker's
`variant-local-uninit.hlsl` (same loop over a *local* rather than an `out` param) is still
completely silent on `main`. This is the highest-value class of finding in this workflow.

### 3708 — verified, including its strongest claim

| Claim | Verdict |
| --- | --- |
| `CheckICE` blacklists the node kind | **Confirmed**: `ExprConstant.cpp:9036`, `case Expr::HLSLVectorElementExprClass: // HLSL Change`. |
| Only a vector-result evaluator exists | **Confirmed**: `VisitHLSLVectorElementExpr` is declared at L5693 and defined at L5706, both on `VectorExprEvaluator`. There is no scalar-result path, which is why `.x` on a `static const` **scalar** fails too — it is the node kind, not the arity. |
| DXC's own test suite pins the behaviour | **Confirmed**, and it is the best finding in the batch — see below. |
| CE link `51xjeKra5` | **HTTP 200.** |

`tools/clang/test/SemaHLSL/const-expr.hlsl` (note: **SemaHLSL**, not `HLSL/` — my first path guess
was wrong, the worker's was right):

```hlsl
// Note: here dxc is different from fxc, where a const integral vector can be used in ICE.
// It would be desirable to have this supported.
float arr_vc_One[vc_One.x];  /* expected-error {{variable length arrays are not supported in HLSL}} fxc-pass {{}} */
```

This reframes the issue entirely. The divergence is not an unknown bug — it has been **known,
tested, and annotated in-tree since 2017**, with the FXC disagreement explicitly recorded
(`fxc-pass`) and a comment saying it would be desirable to support. Two consequences the draft
should carry: the issue is a **decision** awaiting a call, not a discovery; and **any fix must
update this test**, which currently locks the rejecting behaviour in as `expected-error`.

**Grep the test suite before bisecting.** The worker's own lesson, and it is right — an in-tree
test that pins the behaviour dates and characterises it faster and more precisely than a release
scan can.

### Cross-batch defect found via 3708 — double-comment in published CE links

The 3708 worker found that `godbolt-note.txt` must **not** contain `//`, because `annotate()`
prepends the comment marker itself. It caught this only after a doubled marker had already
reached a published, immutable shortlink.

Checked across all 42 `godbolt-note.txt` files in the tree. **Two earlier issues are affected**
and their published links carry `// // What to look for`:

- **2191** — `// What to look for`
- **3259** — `// What to look for: this shader is INVALID -- an amplification-shader payload may not ...`

Cosmetic, but it is visible in public links. CE shortlinks are immutable, so correcting it means
republishing and updating the citation in `comment.md`. Low priority; grouped with the other
pending cleanups rather than fixed mid-batch.

`triage.py` should simply strip a leading `//` in `annotate()` instead of relying on the
convention being remembered. Also flagged by the same worker: `godbolt --source` does **not**
re-derive CE arguments, so switching to a compute restatement silently invalidates every pane —
a much more dangerous version of the same class.

### Superseded links that must never be cited

3708 published and then replaced two shortlinks. Only **`51xjeKra5`** is current;
**`rExz1WG43`** and **`57G1v95WP`** are superseded and must not appear in any report or draft.
Collation should grep for them before publishing.

### 3726 — verified, and it read the maintainer's intent correctly

| Claim | Verdict |
| --- | --- |
| Front end is silent | **Confirmed.** `DiagnosticSemaKinds.td` has 191 `err_hlsl` diagnostics (positive control) and **none** for resource assignment. |
| Rejection comes from the DXIL backend | **Confirmed** in `lib/HLSL/DxilCondenseResources.cpp`, whose `ErrorText[]` table contains the literal strings, including *"exported library functions cannot have resource parameters or return value."* |
| The message is a misleading catch-all | **Supported.** A pixel shader containing no library functions is told about *exported library functions* — the diagnostic names a scenario the shader does not have. |
| `spirv` was removed deliberately | **Confirmed exactly** from the issue timeline: `2024-07-16T17:29:11Z labeled damyanp incorrect-code`, `17:29:21Z unlabeled damyanp spirv`, `17:32:37Z renamed damyanp`. |
| CE link `77EjzsnP9` | **HTTP 200.** |

Two things this worker did that are worth promoting into SKILL.md as standing practice:

**It refused to re-propose a label the maintainer had deliberately removed.** It had strong fresh
SPIR-V evidence (exit 0, no diagnostic, wrong bindings) that would ordinarily justify proposing
`spirv` back. Instead it read the timeline, saw the removal was a considered act by the
maintainer — made in the same minute as adding `incorrect-code` and immediately before a retitle
— and raised it as a **question** rather than a proposal. SKILL.md already says removals need a
reason from the issue itself; this is the mirror case and belongs beside it: *an addition that
reverses a maintainer's explicit decision needs the same bar.*

**It declined `text_stale` for the right reason.** The title no longer matches the original
report, but only because the maintainer **updated it in 2024 to match the defect**. A stale-text
flag would have been technically triggerable and substantively wrong.

**Reader trap to carry into the draft.** The maintainer's own suggestion in-thread — make
`x0/x1/x2` `static` — makes the DXIL path compile *cleanly*. Anyone re-checking this issue by
following that advice will conclude "cannot reproduce". The draft must say so explicitly.

**Genuinely new finding:** three compilers give three different answers on the same input — DXC
DXIL rejects it (late, with a misleading message), DXC SPIR-V accepts it and emits **silent wrong
code** (binding the assignment *targets* `x0/x1/x2` while `r0/r1/r2` never appear), and
`hlsl_clang_trunk` accepts it and lowers the store through `r0`. Controlled with a 2x2 matrix.

**Scope is a design question, correctly left open:** with `static` or function-local resources the
DXIL path compiles correctly, so a blanket Sema rule would reject working code. The worker did not
pre-empt the call, which is right.

### Field discipline is drifting — cosmetic, already defended

`triage.py:77` documents `history` as a token (`always-repro'd|fixed|regressed|unknown`), and
`render_overview.py:177` renders it as a **markdown table cell**. Five issues now hold
multi-hundred-character paragraphs there: 2923 (1319 chars), 2922 (1193), 3237 (762), 2633 (667),
3811 (661).

Checked whether this breaks the generated table: **it does not.** `render_overview.py:100` already
collapses whitespace and escapes `|`, and no structured field in any issue contains a pipe. So
this is a readability drift, not a correctness bug — the content is good and belongs in
`notes.md`, with the token in the field. Worth a line in SKILL.md; not worth a fix-up commit.

### 2604 — verified; the obvious fix is the wrong fix

| Claim | Verdict |
| --- | --- |
| `-Fc` is `DriverOption` only | **Confirmed** at `include/dxc/Support/HLSLOptions.td:505` (note: `include/dxc/Support/`, not `tools/clang/include/clang/Basic/` — my first path guess was wrong, the worker's line number was exact). |
| `opts.AssemblyCode` has no reader in the library | **Confirmed.** `git grep AssemblyCode -- tools/clang/` returns readers **only** in `tools/dxclib/dxc.cpp:378,438,439` (the driver) and `unittests/dxc_batch/dxc_batch.cpp` (a test). **Zero** in `tools/clang/tools/dxcompiler/`. |
| `docs/SPIR-V.rst` is wrong | **Confirmed verbatim**: *"Command-line options supported by SPIR-V CodeGen are listed below. They are also recognized by the library API calls."* followed by ``- ``-Fc``: outputs SPIR-V disassembly to the given file``. Measured false. |

The neighbouring definitions make the gap unusually legible, and the draft should show them:

```
def Fo  : ... Flags<[CoreOption, RewriteOption, DriverOption]>
def Fc  : ... Flags<[DriverOption]>                    <-- the odd one out
def Fe  : ... Flags<[CoreOption, DriverOption]>
def Fd  : ... Flags<[CoreOption, DriverOption]>
def Fre : ... Flags<[CoreOption, DriverOption]>
```

Every `-F*` output option carries `CoreOption` except **`-Fc` and `-Fh`**. `-Fh` is not part of
this issue and was not tested, but it has the identical shape and is worth a maintainer's glance.

**The load-bearing insight, and the real value over the six-year thread:** adding `CoreOption`
would make the option *parse* and nothing more. With no reader in `dxcompiler/` and no `Compile`
path producing `DXC_OUT_DISASSEMBLY`, the one-line patch converts a **loud, correct error into a
silent no-op** — strictly worse for a caller. That is the kind of claim that is only credible
because it was corroborated from source rather than from output.

**A control caught a false positive**, again. v1.4.1907 and v1.5.2003 return the *same*
`0x80070057` for `-spirv` because they have no SPIR-V codegen at all. Without a `-spirv` baseline
guard the worker would have reported "SPIR-V rejects `-Fc` on all 21 releases" — an invented
finding. This is the `invalid-probe` trap wearing yet another face: identical error code, wholly
different cause.

**New hazard worth promoting into SKILL.md: never invent an `@mention`.** The worker nearly
credited the 2020 commenter by handle in a publicly-postable draft; that account is deleted and
returns an empty login. An `@mention` in a posted comment notifies a real person, so a wrong or
invented one is exactly the kind of externally-visible side effect this workflow exists to avoid.
Rule: quote what a commenter said, do not `@`-address them, and never reconstruct a handle.

`bisect` was correctly **not** run — it drives `dxc.exe`, which would have scored every release
`no-repro` and produced a confident "never reproduced" that is the exact inverse of the truth.
This is the fifth occurrence of the harness-vs-bisect mismatch (2918, 2922, 2923, 3237, 2604);
it is now clearly a missing feature rather than a recurring mistake.
