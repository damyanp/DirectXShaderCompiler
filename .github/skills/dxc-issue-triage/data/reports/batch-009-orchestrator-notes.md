# Batch 009 — orchestrator notes

Handover to the collation session, which by design never sees the dispatch conversation.

## The five, and why

| Issue | Filed | Labels | Why it is in this batch |
| --- | --- | --- | --- |
| 2633 | 2020-01 | `enhancement`,`spirv` | SPIR-V library linking — a question-shaped request |
| 3237 | 2020-11 | `bug`,`reflection` | library reflection returns E_FAIL listing parameters |
| 3429 | 2021-02 | `bug` | TGSM pointers must originate from an unambiguous TGSM global |
| 3695 | 2021-04 | `bug`,`crash`,`incorrect-code` | crash on a bad shader |
| 3706 | 2021-04 | `correctness` | uninitialised var as a structured-buffer index |

Mix is deliberate: one SPIR-V enhancement, one reflection, one validation, one crash, one
correctness. Ages 2020-01 to 2021-04.

**3237 has been deferred from two previous batches** because reflection is awkward to measure
from the `dxc` CLI. It is included now precisely because it stresses the method where it is
weakest. If it turns out not to be judgeable by compiling, `not-compiler-verifiable` is the
correct, useful answer — do not force a verdict by inventing a test.

## Ground truth

`main-debug` is registered at **`ab5400907`**, a SHA that **no longer exists** (killed by the
batch-007 message-only history rewrite; live twin `950b58792`, identical tree
`574a2bd25a0b57ea1f450ea3dc0776919fcfe108`).

Re-verified at the start of this batch against upstream `main` at `13730886e`:

```
git diff --name-only ab5400907 FETCH_HEAD  ->  0 files outside .github/skills/
```

So the Debug binary still compiles source byte-identical to upstream `main`. **Do not rebuild
on the SHA mismatch.** Verify provenance by tree; SKILL.md documents this.

## Corrections carried in from batch 008 — already applied, do not re-litigate

- **`audit` is read-only and safe.** Batch 008's worker brief wrongly forbade it alongside
  `reindex`. Fixed: workers are now told to forbid `reindex` only and to *run*
  `audit --issue <N>` as a self-check.
- **`audit` does not re-score anything.** It is a completeness check for missing evidence.
  Re-scoring is `reindex`'s behaviour. An earlier note claimed otherwise; batch 008's
  collation caught it.

## Still open from batch 007, partially addressed in 008

Batch 008 completed the `split_cmd` fix, the timeline check and the worker-brief fix, and
superseded the `script` predicate with "harness-as-compiler". **Still open:** the predicate
`role` marker, re-scoped by batch 008 into a proposed `bisect` change. Pick it up only if it
does not destabilise the tooling; `test_predicates.py` must still pass.

## Hard constraints

- **Never write `#NNNN`, `GH-NNNN`, or an issue/PR URL in a commit message.** Bare numbers
  only. Measured: this created 16 cross-reference events across 14 upstream issues, and one
  reporter followed the reference in and publicly answered an unposted draft.
- **Do not push.** The maintainer is holding pushes pending his review. Commit locally only.
- **Nothing goes to GitHub.** Read-only `gh` only.

## The compression-vs-evidence asymmetry — this is where batch 008 earned its keep

Step 10 reviews `comment.md`. **Nothing reviews `summary` or `text_stale`** — yet those are
read first, quoted most, and reviewed least. Batch 008's collation caught two summaries that
added claims their own correct long-form drafts did not support:

- 2922 said "fixed **by** `c0676c7ca`" when the window holds 248 commits and nothing was built
  in isolation → "the evidence points to".
- 3693 said "FXC rejects **the same source**" when FXC has no raytracing profile and the
  comparison actually used a compute restatement.

Both were caught only because collation read the summary *against* the notes as a separate
pass. **Do that again.** Compression may only remove claims, never introduce one.

`text_stale` is a claim about someone else's writing and needs a high bar. Check the filing
date first.

## Collation checklist

1. `python scripts/triage.py audit` — must exit 0. Read-only completeness check.
2. Re-read every `summary` and `text_stale` *against* its `notes.md`, as its own pass.
3. Cross-issue: does any pair share a root cause? Did two workers hit the same tooling trap?
4. Step 10 independent draft review on a **different model**; record `reviewed_by`.
5. `render_comments.py 009`, then `render_overview.py`.
6. `test_predicates.py` — all must pass.
7. `git status` on `scripts/` and `SKILL.md` to confirm single-writer held.
8. Write `data/reports/batch-009.md`, including what the batch taught about the method.

## Orchestrator findings during batch 009

### The agent `grep` tool is blind to this workspace (workflow-critical)

`.github/` is a hidden directory and ripgrep skips hidden paths by default, so the agent `grep`
tool returns `No matches found` for **every** file in the triage tree. It does not error.
Measured: `grep` for `dxc-issue-triage` across the repo root returned nothing; `Select-String`
found it in 15 files. `glob` is unaffected, so a file can be listed and then silently not
searched.

Two independent sightings this batch: the 3429 worker (single-file query, cross-checked twice)
and me (directory query, on 3009). Recorded in SKILL.md before `## Setup`.

Consequence for collation: **any absence check run with `grep` must be redone with
`Select-String`.** That includes confirming a claim was removed from a draft and scanning for
leaked absolute paths. Commit-message tag scans are safe — they read `git log`, not files. I
re-scanned all 11 triage commit messages with `Select-String` after finding this: clean.

### #3009 has an un-backfilled control gap

3009's `match.json` states "Verified against a control (the same shader with `b.y` also
assigned), which must NOT match", and `notes.md` lists `match.json` as "with its control
documented". There is **no control shader and no capture on disk** — only prose. The control
may well have been run, but nothing left behind can re-check it.

This is not a new lesson: SKILL.md already says *"A control nobody can re-run is not a
control"*, and the `run --shader/--label/--expect` tooling exists because of it. 3009 is an
instance that predates the fix and was never backfilled. Found by the 3706 worker, which
inherited 3009's trap and then persisted four controls of its own.

Worth a sweep of pre-tooling issue dirs for the same pattern; **not** in scope for this batch,
and it must not turn into re-triaging closed work.

### Verdicts verified by the orchestrator

- **3706** — accepted. `warn_uninit_var` is `DefaultIgnore` (`DiagnosticSemaKinds.td:1575`),
  so `-Wall` warns and the default does not. The partial-init control is silent under `-Wall`
  while emitting byte-identical DXIL (same shader hash) — that is the evidence that "just
  enable the warning" closes 3706 but not 3009's shape, and it is why these are related but
  not duplicates. `DxilValidation.cpp:1979` confirms RawBuffer *requires* `undef` in the
  elementOffset slot, so `control-byteaddress.hlsl` is a real trap, not a hypothetical one.
  FXC `error X4000` confirmed in the CE capture.
- **3429** — accepted. `DxilValidation.cpp:3821-3848`: the pointer walk runs only when the
  instruction `isa<GetElementPtrInst>` or `isa<BitCastInst>`; a `phi` falls to the `else` and
  is rejected without examination. The in-source comment shows the walk was added for SM 6.9
  arrays-of-vectors, so `phi` was never in scope. This corroborates the worker's central
  claim that the pointer is not in fact ambiguous.

### Correction: the `grep` blindness is a missing-`glob` trigger, not hidden paths

My first diagnosis in this file (ripgrep skipping `.github` because it is hidden) was **wrong**.
The 3429 worker ran controlled probes and located the trigger as the **absence of a `glob`
filter**; I then confirmed it with a back-to-back A/B on an identical pattern and directory:
with `glob: *.md` the file is found, without a glob the same query returns `No matches found`.
Combined tally: 7/7 glob-less queries false-zeroed, 4/4 glob'd queries accurate.

SKILL.md has been corrected to describe the trigger rather than my mechanism. The operational
rule is unchanged and is what matters: **use `Select-String` or `git grep` whenever a zero
result would be meaningful.**

Worth recording as a workflow observation in the batch report: a worker corrected the
orchestrator, with better evidence than the orchestrator had. That is the review direction
working as intended, and it is an argument for briefing workers with provisional findings
rather than settled ones.

### Path-leak scan across batch 009

Run with `Select-String` over every artifact directory. Two hits:

- `3429/issue.json` — contains `D:\local\Temp\...` and `C:\Users\n\Downloads\...`. **Benign.**
  These are the *reporter's* paths, quoted verbatim from the public issue body by
  `triage.py fetch`. Already public; nothing to redact.
- `3237/measure.json` — contains this machine's checkout path (`<repo>\...`).
  **Genuine.** Everything `triage.py run` writes is redacted to `<repo>` / `<cache>`; a
  worker-authored harness bypassed that convention. Sent back for regeneration.

Follow-up for collation: `3237` also has a `bin\` directory. I have asked whether it holds a
committed **binary** (`refl3237.exe`). If so it should almost certainly not be committed —
SKILL.md's storage split commits evidence and excludes anything huge, machine-specific or
derived. Prefer harness source plus the exact build command.

### Verdicts verified by the orchestrator (continued)

- **3695** — accepted. Debug exit `0xE0000001`, and v1.4.1907 crashes at `0xC0000005` with
  **empty stdout and stderr**, which is direct confirmation that a message-based predicate
  would have faked a fix boundary and that `internal_failure` was required. Its decision *not*
  to set `text_stale` is correct and well-argued: the attached repro reproduces first try, so
  the trigger detail is a refinement, not staleness. Its ANSI-escape finding is real — I
  counted 278 and 86 `0x1b` bytes in two CE captures.
- **2633** — accepted, and it is the batch's most valuable finding. Proven from source, not
  merely observed: `git grep` finds **zero** `LinkageType::Import` call sites in
  `tools/clang/lib/SPIRV`, against exactly one `LinkageType::Export` at
  `DeclResultIdMapper.cpp:1826`. The export/import asymmetry the worker measured from output
  is visible directly in the front end. `-default-linkage` is confirmed DXIL-side
  (`DxilConstants.h`, `HLModule.h`). The draft is well-judged in tone: it leads with "half of
  this already works" and keeps the "2020 answers are now false" observation in the internal
  `text_stale` field rather than arguing with named contributors on the thread.
- **3429** — accepted after the `-O0`/`-O2` gap was closed. All five optimization levels now
  have tool-made captures. The new probes produced a better mechanism than the original
  claim: at `-O0` no `phi` of groupshared pointers is formed at all, so the pointer `phi` is
  *created by optimization* from `-O1` up. Also a second, independent justification for the
  loosened predicate — `-O1`/`-O2` number the phis differently from `-O3`, so an
  instruction-text anchor would have scored them no-repro.

All four CE shortlinks re-verified by me independently (HTTP 200, pane counts and arguments
matching each draft): 3706 `n9YeYKT3W`, 3429 `61Gb43GjM`, 3695 `aqPedMGE4`, 2633 `ca49jMrrc`.

### 3237 storage question — already answered by the worker

I asked whether `refl3237.exe` was a committed binary. It is not, and the worker had handled it
before being asked: `data/issues/3237/.gitignore` excludes `bin/` and `bin-build.log`, and what
is committed instead is the harness **source** (`refl3237.cpp`), a build script
(`build-refl3237.cmd`) and a runner (`run-refl3237.cmd`). `git check-ignore -v` confirms both
`refl3237.exe` (45 KB) and `refl3237.obj` (226 KB) are genuinely excluded.

The build script derives every path from `%~dp0` with no absolute paths, and documents the
`Program Files (x86)` close-paren hazard that breaks `if (...)` blocks in `.cmd` — a trap worth
keeping. This is the right resolution of SKILL.md's storage split and should be the pattern for
any future harness: commit source plus an exact build command, never the binary.

Only `measure.json`'s absolute paths remain outstanding for 3237.

### Summary-vs-notes support pass (checklist item 2)

Done as its own pass over all five `summary` fields. No unsupported claims found this batch —
the 8737 failure mode did not recur. The two that asserted the most were checked hardest:

- **3695** names a specific pass, which the compiler output never prints. Backed:
  `manual-case-assert-stack.txt` shows `assert(Val && "isa<> used on a null pointer")` inside
  `DxilLowerCreateHandleForLib::ReplaceResourceUserWithHandle`, reached via `runOnModule` ->
  `GenerateDxilResourceHandles` -> `TranslateDxilResourceUses`.
- **3429** was the one gap and it is now closed with tool-made captures at all five levels.

One qualitative note for the report: 3429's `summary` is very long — accurate throughout, but it
carries a CAUTION clause aimed at future triagers. That is worth keeping somewhere; whether the
`summary` field is the right home is a judgement call for collation, not an accuracy defect.

### Systemic finding: absolute paths in committed evidence (and my own scan was wrong)

`triage.py` redacts machine paths in the captures **it** writes (`display_exe`, triage.py:196 --
`<cache>`, `<triage>`, `<repo>`, most-specific-first, forward slashes; the docstring gives the
rationale: "an absolute path bakes one contributor's directory layout into the repo"). Anything
written **by hand or by a per-issue harness** bypasses that.

My first scan reported 3 of 5 batch-009 directories clean. **That was a false clean**, from the
same class of bug I had just written into SKILL.md: I used the literal pattern `C:\\prj`, which
matches JSON's escaped form but not the single-backslash form in `.txt` captures. The 3237
worker independently hit the mirror-image version (a regex for `C:\prj\` missing JSON's
`C:\\prj\\`) and — unlike me — validated its scan against a known-positive first. That step is
what separated its correct result from my wrong one.

Corrected scan, pattern validated against all three spellings before use: **36 files across 20
issues and 9 batches**, not a batch-009 problem.

Actions taken this batch:

- **Scoped fix applied to batch 009 only** (9 files in 2633, 3429, 3695), using the identical
  transformation `display_exe` applies. Verified afterwards with the positive-controlled
  pattern: all five directories clean.
- **Evidence integrity checked on the hardest case.** `3695/manual-case-assert-stack.txt` is
  captured debugger output. After redaction the cdb invocation, the assert text, the
  `Casting.h(96)` location and every frame naming `DxilLowerCreateHandleForLib` are intact;
  only the personal path prefix is tokenised. `C:\Program Files (x86)\...` is deliberately
  **kept** -- it is a system path and part of the literal command.
- **Executable files excluded from tokenisation.** Rewriting a path inside a `.py`/`.cmd`
  makes it non-runnable, not portable. `2633/probe-powershell-hazards.py` hardcoded
  `DXC = r"C:\prj\..."`; fixed properly by deriving the repo root from `__file__` (six levels
  up) with a `DXC_EXE` override and an explicit not-found error. Verified: resolves to the real
  `dxc.exe`, compiles, no path remains.
- **`3237/method-notes.md` deliberately NOT redacted.** It documents the backslash-escaping
  trap and quotes `C:\prj\` and `C:\\prj\\` as its evidence; rewriting them destroys the lesson.

**Outstanding, needs a decision:** ~27 files across batches 001-008 still carry absolute paths,
including `2922/artifacts/measure.json` (42 lines) and `2923/manual-case-history.txt` (260).
Deliberately not touched -- that is a cross-batch change to already-committed evidence and
belongs in its own clearly-labelled commit, not folded into batch 009. The script is ready.

**Tooling recommendation for collation:** this is the third absence check to fail silently in
one batch, and `audit` cannot see any of them. The durable fix is the same one that worked for
controls (`run --expect`): make it a gate. `audit` should scan committed text artifacts for
machine-absolute paths and report file:line, with `issue.json` excluded as fetched public text.
A reminder will not survive; a check will.
