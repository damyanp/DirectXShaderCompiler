---
name: dxc-issue-triage
description: Triage open DirectXShaderCompiler GitHub issues by determining whether each has a usable repro, whether it still reproduces against a current build, and which release fixed or regressed it. Use when asked to triage, audit, or spot-check DXC issues, to find stale/fixed issues in the backlog, or to check whether a specific issue still reproduces. Produces an evidence-backed report and makes no changes to issues or to DXC source.
---

# DXC issue triage

Determine, for each open DXC issue: **is there a usable repro, does it still reproduce, and
when did that change?** Produce a report backed by on-disk evidence.

## Hard rules

- **Read-only on GitHub.** Only `gh issue view/list`, `gh release list/view/download`,
  `gh api` GET. Never `gh issue edit|comment|close|reopen|label`, even if a verdict seems
  obvious. Drafting a comment is in scope; **posting it is not**. Recommending an action and
  taking it are different jobs.
- **Never write an issue reference into a commit message.** `#1234`, `GH-1234` and issue or
  PR URLs all create a **cross-reference event on the issue itself**, visible to everyone
  watching it — which is posting to the issue by another route, and breaks the read-only rule
  just as surely as `gh issue comment`. Use bare numbers: `triage: batch 006 (2128, 2331)`.
  This fires even from a personal fork, and it is attributed to whoever pushed.

  > Measured: pushing three batch commits created **16 cross-references across 14 issues**.
  > On one of them the reporter followed the link within hours, read an *unposted draft* plus
  > a one-line summary that compressed a correct analysis into a false claim, and reasonably
  > answered it as though it were the project's position. The maintainer had to apologise
  > publicly. Rewriting the messages afterwards does not retract the events.
  >
  > The blast radius is wider than the noise: a cross-reference makes the whole triage branch
  > discoverable from the issue, so **every draft becomes de-facto published**. Write drafts
  > as if a reporter will read them unreviewed, because one did.

- **Never modify DXC source** while triaging. The point is to measure the compiler as it is.
- **Only public repros go to Compiler Explorer.** `godbolt` uploads the shader to a public
  third-party service. Repros derived from public issues in this public repo are fine;
  anything from a private report, a customer, or unreleased work is not.
- **Evidence or it didn't happen.** Every verdict must be reproducible by a human from the
  files left behind: the repro, the exact command, and the captured output.
- **Batch and checkpoint.** Triage a handful of issues, then stop and let a human review
  before continuing. Verdict quality degrades silently; unattended full passes hide that.

## How much should live in one session?

**One session per issue, run in parallel, plus a collation session per batch.**

The tempting argument for long sessions — that cross-issue context is what finds method bugs —
does not survive checking. Of the 16 method lessons in the first three batch reports, **13 were
discovered inside a single issue**, 2 came from the batch-level draft review, and 1 came from
`reindex` re-scoring, which uses no session context at all. A seventeenth was found by an agent
given *no* context at all. What actually crossed issues was **re-recognising** an already-known
trap, and that is collation work, not discovery work.

Meanwhile long sessions cost real quality. After four issues that still reproduce, the fifth
gets less scrutiny. And a session spanning a batch will be compacted mid-flight, so its later
issues are analysed against a summary of the method rather than the method — that is not
hypothetical, it happened during batch 003.

| phase | job |
| --- | --- |
| **open** | select the batch, `labels --refresh`, confirm the ground-truth build |
| **per issue** | steps 1–9 and 11 for exactly one issue. Parallel. Touches only that issue's directory |
| **collate** | `reindex`, cross-issue patterns, duplicates, step 10's review, the batch report, and promoting method lessons into `SKILL.md` / `triage.py` |

**Collation is itself a fresh session, briefed only by what is on disk.** It is given the batch
number and the artifact directory, and nothing else — not the workers' summaries, not the
orchestrator's recollection. This costs a re-read of every issue, and buys the one check
nothing else performs: if a finding cannot be reconstructed from `data/issues/<nnnn>/`, it is
not yet evidence, and collation will simply fail to find it. A batch where collation cannot
rebuild the report is a batch whose artifacts are incomplete, which is exactly the defect that
`#3038`'s uncaptured control and `#3150`'s unwritten measurements both were.

Two rules make the parallelism safe:

- **A per-issue session never writes shared state.** It does not edit `SKILL.md` or
  `triage.py`, because a predicate change mid-batch would invalidate verdicts other sessions
  have already written, and concurrent edits collide. Method observations go in
  `issues/<nnnn>/method-notes.md`; collation promotes them. Single writer. Verify it held —
  `git status` on `scripts/` and `SKILL.md` after the parallel phase should be empty.
- **The database is shared state too, and `reindex` rewrites all of it.** It opens
  `DELETE FROM issues; DELETE FROM runs;` and rebuilds from whatever is on disk at that
  instant, so a worker running it mid-batch deletes rows its peers are still writing. In batch
  004 all five workers ran it — it was the only completeness check available — and #2191 lost
  its title, url, created_at and `batch`, which would have dropped it from its own report. Use
  **`triage.py audit --issue <n>`** instead: same completeness check, reads no tables and
  writes none. `reindex` is collation's command.
- **Collation runs `reindex` before writing anything.** Because probes are re-scored rather
  than restored, any lesson promoted during collation is applied retroactively to every issue
  in the batch — including the ones triaged before it was learned. That is what buys back the
  lesson-propagation a parallel batch would otherwise lose.

The shared *cache* is different from shared state, and is safe to contend on: `ensure_release`
takes a per-tag lock, downloads to a scratch directory and moves the finished archive into
place, so concurrent workers cannot see a half-written zip. This matters more than it sounds —
`bisect` probes both endpoints first, so on a cold cache every worker in the batch asks for the
oldest and newest releases within seconds of each other. The database runs in WAL mode with a
60-second busy timeout for the same reason.

The rule that makes any of this work is that **the conversation is never where a fact lives.**
Two kinds of context, two destinations:

| context | belongs in | example |
| --- | --- | --- |
| about the **method** | `SKILL.md`, `triage.py`, its tests | "absence predicates are satisfied by a failed parse" |
| about a **verdict** | that issue's artifacts | why this repro, why this predicate, what the control proves |

Anything that exists only in the conversation is a defect, whether or not it is correct.

### Briefing a per-issue worker

Whether the worker is a separate session or a subagent, the brief is what makes or breaks the
isolation — it is the one place cross-issue context can leak back in. Give it:

- **its issue number and nothing about the others.** No "like #3873", no "the previous issue
  showed", no list of what else is in the batch. If a trap is worth warning about, it belongs
  in this file, where every future batch gets it too;
- the path to this skill, and the instruction to follow it;
- the ground-truth compiler id, and the reminder to verify `dxc --version`;
- the boundary: it writes only `data/issues/<nnnn>/`, and records method observations in
  `method-notes.md` rather than editing `SKILL.md` or `triage.py`;
- the check it may run: `triage.py audit --issue <n>`. **Not `reindex`** — that rewrites the
  whole database and will delete peers' rows;
- the stop condition: verdict recorded and draft written, or a clear statement of what blocked
  it. `inconclusive` is a real outcome; a forced verdict is not.

Two things belong to the batch, not the issue, so tell the worker not to attempt them:
`reviewed_by` (step 10 runs once over all the drafts) and any cross-issue claim. A worker that
finds itself wanting to say "this is the same as #NNNN" should say so in `method-notes.md` and
leave the draft silent; collation is where that judgement can actually be checked.

**A brief may name a hazard; it must not predict the verdict.** "This one is a diagnostic, so
watch the `invalid-probe` classifier" is orienting. "History will be unmeasurable because
`lib_6_9` is too new" is an answer, and the worker's job is to find the answer. #8725's brief
said exactly that and the worker disproved it — five of twenty releases can express `lib_6_9`
and all five reproduce — but a less careful worker would have recorded the prediction as the
result and nothing on disk would have contradicted it. If you catch yourself writing an
expected outcome into a brief, write the hazard instead and let the evidence decide.

A subagent is weaker isolation than a real session: it shares the working directory, and it
returns its findings into the orchestrator's context rather than only to disk. The first is
handled by the locking above. The second is acceptable, because the orchestrator *is*
collation. What is not acceptable is the orchestrator answering from memory what the worker
should have answered from evidence — if a fact is not in `data/issues/<nnnn>/`, it did not
happen.

When collation is a fresh session, that hazard disappears by construction: a worker's summary
that never reached disk is unavailable to anyone. Prefer that arrangement. It converts the
single-writer rule from a discipline into a property of the setup.

### What `reindex` guarantees, and what it does not

Parallel triage leans entirely on mechanical checking, so know its edges. `reindex` re-scores
every probe with today's predicate code — primary captures **and** labelled variants — flags
probes whose command `cmd.txt` no longer specifies, re-checks every control against its
declared `--expect`, and audits each issue for evidence a completed triage should have left
behind.

Variants were re-scored only against their `--expect` until batch 005, so a control's own
`# verdict:` line could disagree with today's code indefinitely and nothing would say so. The
first run of the extended check found three such lines in #2202, stale since batch 003 — their
declared expectation had been satisfied the whole time while the header beneath it said the
opposite.

It cannot check reasoning. It will not tell you a repro is unfaithful to the issue, that the
predicate tests the wrong thing, or that a verdict misreads its own output. That is what the
human gate and the blind test are for.

It also cannot check what it cannot see. The rebuild reads `issues` from `verdict.json`
alone, so any column written by another subcommand — `title`, `url`, `created_at`, `labels`
from `fetch`; `godbolt_url` from `godbolt` — is reconstructed from nothing. It now carries
those forward from the previous rows and prints what it kept, but a field that lives only in
the database is one fresh clone away from being lost. When `reindex` reports fields kept,
write them into `verdict.json` with `verdict --<field>`.

**Disagreements have to be closed, not accumulated.** When a predicate improves, every header
scored under the old code disagrees, and a permanent list of known-stale lines is where the
next real disagreement hides. Investigate each one, then `reindex --accept` to restamp the
`# verdict:` headers — the verdict is derived from the captured text, so nothing is lost.
For a control whose *declared* expectation is what went stale, use
`triage.py expect --issue N --capture <file> --expect <value>`, which rewrites that one line
and refuses if the new declaration would itself be false. Neither command touches a
measurement. Never hand-edit a capture: `# exit:` and the output below it are observations.

### Test reproducibility, don't assume it

Give a fresh agent **only** one issue directory — barring `notes.md`, `verdict.json` and
`comment.md`, which contain the conclusion — and ask it to state status, history, repro
quality, suggested action, which releases are invalid evidence, and *what it could not
determine*. Then compare.

Run it on at least one issue per batch, and always on any issue whose suggested action is
`close-fixed`: recommending a close is the highest-stakes verdict, and the one most likely to
be acted on without re-checking.

Measured on #3038, this reproduced the transition (v1.8.2502 → v1.8.2505), the repro quality,
the suggested action, and the rejection of v1.4.1907 as unprobeable — and then found a real
defect: **the control had no captured output.** It had been run by hand, its result published
in a draft comment, and the evidence never written down. The claim was true and unsupported at
the same time, which is the failure mode this whole workflow exists to prevent.

The lesson generalised into tooling rather than a reminder: `run --shader X --label Y --expect`
makes capturing a control the easy path, because a step that depends on remembering to do it by
hand is a step that will be skipped. **A control nobody can re-run is not a control.**

## Setup

Artifacts and cache live in **two separate roots**, and the split is the whole storage
design:

| root | default | committed? |
| --- | --- | --- |
| `DXC_TRIAGE_ROOT` | `<skill>/data` | **yes** — repros, captured output, notes, verdicts |
| `DXC_TRIAGE_CACHE` | `<skill>/.cache` | no — release binaries (~1.2 GB) and the database |

Evidence is committed because a verdict nobody can re-check is just an assertion. The cache
is not, because it is either huge, machine-specific, or derived. `scripts/triage.py` is the
only tool you need.

```bash
python triage.py init                        # first time only
python triage.py reindex                     # after a fresh clone: rebuild db from data/
python triage.py catalog --seed-from <repo>/build/tools/clang/test/dxc_releases
```

`catalog` records every release that ships a `dxc` binary. Ordering uses the **build date
encoded in the asset name**, not the publish date — servicing patches ship long after the
snapshot they were built from. `--seed-from` adopts release trees the DXC test infrastructure
already downloaded, for free.

### `reindex` is a regression test over every past batch

Run verdicts are not stored and restored — they are **re-derived** by running today's
predicate code over the archived output. So a rebuild re-checks every probe ever captured
and reports two kinds of disagreement:

- **probes today's code scores differently.** A predicate bug found while triaging one issue
  is retroactively applied to every issue already triaged. Both wrong-verdict classes found
  so far — a release rejecting an unknown profile, and an absence predicate satisfied by a
  failed parse — would have surfaced here automatically, for free.
- **probes captured with a command `cmd.txt` no longer specifies.** Correcting a repro does
  not delete the outputs captured from the old one, and a superseded probe looks exactly as
  authoritative as a current one.

The second check found two real cases the moment it was written. Three #3873 probes still
held `-T ps_6_7` output after the profile was corrected to `ps_6_0` — `bisect` short-circuits
once both endpoints agree, so it never revisited them. Worse, **all 21** of #3768's probes
still carried the `-fcgl -Vd` workaround after it had been removed from `cmd.txt`: the
removal had been confirmed by hand but never re-recorded, so the entire published history
rested on a configuration the report said was no longer in use. Re-running both confirmed the
verdicts rather than overturning them — but neither gap was visible without this check, and
"the verdict happened to survive" is not the same as "the evidence supported it".

Run it at the end of every batch. A clean run prints `every probe re-scores as captured, and
none are stale`; anything else is a finding to explain before the batch is written up.

**Name auxiliary captures so they are not mistaken for probes.** `out-<compiler>.txt` means
"the primary repro, scored by `match.json`". A control shader, a compute-shader translation
or a hand-run command line is *not* that, and scoring it with the primary predicate produces
a spurious disagreement — #1702's compute variant legitimately emits an error the pixel
repro does not. Use `variant-*.txt` for controls and translations, `manual-case-*.txt` where
the repro is not a `dxc` invocation at all.

### The ground-truth compiler must be a clean Debug build

Build `dxc` in **Debug** from a clean checkout of the target branch. Debug matters: a large
share of old DXC issues are asserts, and Release builds have asserts compiled out.

```bash
cmake --build <build> --config Debug --target dxc --parallel
python triage.py compiler --id main-debug --exe <build>/Debug/bin/dxc --commit $(git rev-parse HEAD)
```

**Verify the version string before trusting anything.** DXC caches generated version headers
and does *not* regenerate them when you switch branches, so a freshly built binary can report
a stale branch and a spurious `-dirty`. If `dxc --version` does not match the commit you built:

```bash
rm <build>/utils/version/version.inc* <build>/utils/version/dxcversion.inc*
cmake --build <build> --config Debug --target dxc --parallel
```

Triage provenance is worthless if the binary misreports what it is.

## Per-issue workflow

### 1. Read the whole issue, comments included

```bash
python triage.py fetch --issue <N> --batch batch-001
```

Comments routinely hold the real repro, a smaller reproducer, a maintainer's design position,
or a prior "still repros in X" datapoint. They also frequently contradict the issue body —
which is itself a finding worth reporting.

### 2. Write down the symptom *before* running anything

Create `issues/<nnnn>/expected.md` stating what "this reproduces" means, derived from the
issue text. **Do this first.** If you run the compiler first, you will rationalise whatever it
printed into a verdict, and "does not reproduce" becomes unfalsifiable.

Record the repro quality honestly: `complete`, `partial`, `prose-only`, `none`, or
`agent-constructed`.

### 3. Build the repro

Write `repro.hlsl` (and any extra files) plus `cmd.txt` — one dxc invocation per line,
**arguments only**, no exe path, paths relative to the issue directory:

```
-T gs_6_0 -E main repro.hlsl
```

Every compiler gets the identical command, which is what makes bisection meaningful. SPIR-V
issues need `-spirv`. If the issue has no repro, construct a best-effort one and mark it
`agent-constructed` — a constructed repro that is clearly labelled is far more useful than
"no repro provided".

> **Reproduce the reporter's exact configuration, then question their workarounds.**
> Two failure modes, both seen on #3768:
>
> *Silently changing the configuration.* The issue was reported against `ps_6_0`; the test
> file's `RUN:` line said `cs_6_0`, and the repro was built from the `RUN:` line. That happened
> to behave identically, but it was luck — the profile is part of what was reported. Use what
> the reporter used, and if you also test something else, say so.
>
> *Inheriting a stale workaround.* #3768 was filed with `-fcgl -Vd` "to disable legalization,
> since there's a current spirv-tools issue that would crash and confuse issues". Copying that
> into `cmd.txt` silently disabled legalization and validation for the entire history search,
> so a whole phase of the compiler was never exercised. Re-test without such flags: the
> upstream bug they dodge is often long fixed. Here removing them changed nothing about the
> verdict, but it did widen the code under test and it revealed that the workaround had never
> been suppressing this defect anyway — the reported stack was in `Sema`, reached long before
> legalization runs.
>
> Keep the original as `cmd-as-filed.txt` and note in `cmd.txt` why it differs.

> **A committed repro must be runnable from the repo alone.** Two things break this silently,
> and both were found by re-running #2427's hand-driven `run-2427.cmd` months after it was
> written. It hardcoded an absolute path to one contributor's `dxc.exe`; and it depended on an
> output directory that git cannot track, because **git does not store empty directories**.
> With `dbgdir/` missing, every case failed with `cannot find the path specified` — the same
> exit status as the real bug, for an entirely unrelated reason, which is precisely the
> `invalid-probe` trap in a manual costume. Take the compiler path from a variable, create any
> directory the repro needs from inside the repro, and gitignore what it emits.

> **Getting a stack out of a crash needs the incantation that matches the failure.** An assert
> arrives two different ways in DXC and the debugger command differs; both are in use.
>
> ```bat
> :: __debugbreak()-style DXASSERT: exit 0x80000003, a trap. Just run to it.
> cdb -c "g;kn 40;q" <dxc.exe> <args...>
>
> :: ...and to continue PAST that trap, `gh` it: run to the trap, step over it, then look.
> cdb -c "g;gh;.lastevent;kn 14;q" -- <dxc.exe> <args...>
>
> :: C++-exception assert: exit 0xE0000001. Break on the exception itself.
> cdb -c "sxe -c \"kb 8; gh\" e0000001; g; q" <dxc.exe> <args...>
> ```
>
> `gh` ("go handled") **emulates `NDEBUG`** in *both* forms: continuing past the assert runs the
> code the release build would have run, so a Debug binary can reproduce the reporter's Release
> symptom without building one. That is how #8725 showed the assert and the invalid `bitcast`
> it guards are the same defect, and how #3251 predicted its release failure mode *before* the
> twenty-release scan ran. Chain one `gh` per assert to walk further — and add
> `sxe -c "gh" e0000001` in the same command line if a *later* LLVM assert (which does throw)
> stands in the way. Which form you meet depends only on which macro the failing code used, so
> keep both to hand. `cdb.exe` ships with the Windows SDK
> debuggers (`C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\`). Trim the capture to the
> header, the assert line and the frames before committing it — a full stack dump is noise.
>
> Note that dxc's assert output puts the value of `File:` on the *following* line, so reading
> only the first line attributes the assert to the wrong file.

### 4. Define the symptom predicate

`match.json` encodes "the symptom is present" so the same test is applied to every compiler
and a human can re-check it later. Include a `note` explaining the choice.

| kind | present when |
| --- | --- |
| `internal_failure` | dxc failed internally — **use this for all crash/assert issues** |
| `regex` / `not_regex` | pattern (absent) in combined output |
| `contains` / `not_contains` | literal substring (absent) |
| `nonzero_exit`, `timeout` | exit code / hang |
| `any_of` / `all_of` | `value` is a list of sub-predicates — for one defect with several signatures |

Add `"invert": true` to negate.

> **Use `internal_failure` for anything crash-shaped.** This is the single biggest source of
> wrong verdicts. The *same* bug surfaces differently across builds — a trapped assert
> (0x80000003) in an assert-enabled Debug build, but an access violation (0xC0000005) or a
> stray `llvm::cast<X>() argument of incompatible type!` E_FAIL in Release release-binaries.
> A predicate matching the assert *message* reports every release as clean, producing a false
> "fixed" verdict. This affects every `crash`-labelled issue.

> **Do not equate "nonzero exit" with "crashed".** On Windows dxc returns **E_FAIL
> (0x80004005) for ordinary diagnosed errors** — a plain syntax error, an invalid target
> profile and a DXIL validation failure all exit with it. A predicate of "anything that is not
> 0 or 1 is a crash" therefore reports essentially every failing compile as an internal
> failure. That is the more dangerous direction of error, because it *invents* bugs rather
> than missing them. `is_internal_failure()` instead tests the specific status codes dxc's own
> exception filter recognises (`tools/clang/tools/dxclib/dxc.cpp`): 0xC0000005, 0xC00000FD,
> 0x80000003, 0xE0000001-3, any other 0xC/0xE structured exception, and POSIX signal exits
> (139 = SIGSEGV) for Compiler Explorer's Linux builds.

**Exit codes, measured — not assumed:**

| Outcome | Exit | Internal failure? |
| --- | --- | --- |
| success | 0 | no |
| input file not found | 1 | no |
| syntax error, invalid profile, **DXIL validation failure** | 0x80004005 (E_FAIL) | **no** |
| `llvm::cast<X>()` type mismatch | 0x80004005 (E_FAIL) | **yes — text only** |
| assert fires (Debug) | 0x80000003, or 0xE0000001 | yes |
| access violation | 0xC0000005 | yes |
| `llvm_unreachable` / `report_fatal_error` | 0xE0000002 / 0xE0000003 | yes |
| killed by signal (Linux/CE) | 139, 134 | yes |

> Two rows fight each other, and both are measured. A bad `llvm::cast` throws
> `hlsl::Exception(DXC_E_LLVM_CAST_ERROR, …)` (`lib/Support/ErrorHandling.cpp`), which the
> driver reports as **E_FAIL — the same status as a syntax error** (#8737). It is the one
> internal failure the exit code cannot distinguish, which is why `is_internal_failure` also
> carries text markers. Conversely #2191's assert exits **0xE0000001**, not 0x80000003,
> because it too arrives as a C++ exception rather than a trap. Do not infer either direction
> from the exit code alone.

> Unrecognised `/`-style flags are **silently ignored** — `/ZZZNONSENSE` exits 0. Never infer
> that a flag was honoured from a clean exit; make it fail (point it at a missing file) to
> prove it was parsed at all.

> **Message text is not portable.** The same failure is worded differently across platforms:
> the Windows build prints `llvm::cast<X>()` where the Linux build behind Compiler Explorer
> prints plain `cast<X>()`. Any marker you add must be build-agnostic, or it will score a real
> crash as clean on some builds. Prefer the exit code; treat text markers as a backstop, and
> assume a predicate tested against a single build is not yet tested.
>
> **It is not portable across release ages of the same compiler on the same platform either,
> and an internal failure may print nothing at all.** #3259's v1.5.2010 access-violates with
> completely empty stderr while every later release prints
> `Internal compiler error: access violation`. A predicate matching that text would have
> invented a fix boundary at the exact release the issue was filed against. This is the reason
> `internal_failure` is defined on the exit status first and the text second — never write a
> crash predicate that depends on the crash saying anything.

**An issue may need more than one predicate.** When the reported symptom differs from current
behaviour, add e.g. `match-crash.json` and bisect each separately. That is how you distinguish
"this was fixed" from "this changed shape but is still broken" — a distinction that collapses
into a misleading single verdict otherwise. Each predicate's probes get their own filenames
(`out-<compiler>--<predicate>.txt`), so the two histories sit side by side; until batch 004
they did not, and #2191's second bisection overwrote 20 of the first's 21 captures with
nothing in the tree to say it had happened. The runner now refuses an overwrite that would
cross predicates, but the shape of the trap is general: **a probe is identified by its
question, not just by the compiler that answered it.**

**One defect can have two signatures — compose predicates with `any_of` / `all_of`.** A bug
whose Release manifestation differs from its Debug one needs a disjunction, or whichever build
you happen to run will report it fixed:

```json
{ "kind": "any_of",
  "value": [ { "kind": "timeout" }, { "kind": "internal_failure" } ] }
```

> Measured on #3873: a Release build **hangs unboundedly** on the repro, while the clean `main`
> **Debug** build trips an LLVM assert in ~2 seconds on the same input — Debug asserts on the
> broken state that Release spins on. A bare `timeout` predicate scores the Debug ground truth
> as `no-repro` and reports this open, always-reproducing bug as **fixed**. Neither signature
> alone is the symptom; failing to compile a valid shader is.

**Give every text-based predicate a control.** The control discipline in step 7 applies to
predicates too: run the predicate against an input you *know* is good, and require it not to
match. A predicate that matches everything is indistinguishable from a bug that reproduces
everywhere.

```bash
python triage.py run --issue <N> --shader control-separate-raydesc.hlsl \
    --label control --expect no-match
```

`--shader` reuses the repro's exact arguments against a different source, so the control and
the repro differ in exactly one way. Use `--args` instead when the variant changes shader
stage and therefore cannot reuse the command. Output goes to
`variant-<label>-<compiler>.txt`, which is deliberately *not* scored as a probe of the primary
repro — a control that behaves differently is the point, not a disagreement to chase.

**Always declare `--expect`.** It is recorded in the output header and re-checked on every
`reindex`, which turns the control from an observation into a permanent assertion. It runs in
both directions, and both are real:

| | |
| --- | --- |
| `--expect no-match` | a **negative** control: a known-good input the predicate must not fire on. #3009's predicate matched a fully-correct shader until it was narrowed |
| `--expect match` | an **identity** control: #1803's shader declared `column_major` must produce *identical* DXIL to the `row_major` original, because that identity is what proves the attribute is ignored |

Getting this backwards is easy and the check catches it: a blanket "warn if a control matches"
rule reports #1803's central finding as a predicate bug.

> **Capture the control, every time.** #3038's control was run by hand and its result quoted
> in the report and the draft comment, but the output was never written down — a published
> claim that existed only in the operator's memory. It happened to be true. `reindex` now
> fails an issue that has a shader with no captured output, because a control nobody can
> re-run is not a control.

> Measured on #3009: a predicate matching any `undef` operand of any `dx.op` **also matched a
> fully-correct shader**, because several DXIL ops carry structurally-undef operands in
> perfectly valid code — `loadInput`'s trailing `gsVertexAxis` is `undef` in every non-GS
> shader, and `bufferStore`'s unused coordinates are `undef` for non-structured buffers.
> Narrowing it to `undef` reaching an *arithmetic* op made it discriminate. Record the control
> in the predicate's `note` so the next person does not have to rediscover it.

### 5. Run against the ground-truth build

```bash
python triage.py run --issue <N>
python triage.py run --issue <N> --match match-crash.json   # extra predicate
```

> **`--shader` and `--args` are not interchangeable.** `run --shader X --label Y` reuses
> `cmd.txt`'s flags and swaps only the source operand, which is what makes a control differ
> from the repro in exactly one way. `run --args "..."` replaces the **entire** command — the
> filename included — and bypasses `cmd.txt` completely. Used without `--label` it therefore
> overwrites the *primary* capture with a command `cmd.txt` does not specify; `reindex` catches
> the mismatch, but `reindex` is a collation-only command, so on #3259 the primary capture sat
> stale for the length of the triage. `run` now warns at capture time. Reach for `--shader`
> unless the stage or flag set genuinely has to change.

> **Editing a captured repro's comments invalidates the capture.** Assert and diagnostic output
> quotes `Line:` numbers, so tidying a comment after the fact silently desynchronises every
> line number in every file you have already written. Preserve the line count, or re-capture.
> Noticed on #2530.

Then classify against `expected.md`:

| status | meaning |
| --- | --- |
| `repros` | reported symptom still observed |
| `does-not-repro` | repro runs clean, symptom gone |
| `changed-behavior` | still misbehaves, differently than reported |
| `not-compiler-verifiable` | needs GPU/runtime/driver/D3D execution to judge |
| `inconclusive` | repro too ambiguous to judge |

`not-compiler-verifiable` is a legitimate, useful outcome — not a failure. Do not force a
verdict on a rendering-artifact or driver-behaviour issue by compiling it.

> **Before you interpret a single probe, check whether the issue is filed against code that is
> not merged.** An issue that names a branch or a PR is not a claim about `main` at all, and
> every probe you run against ground truth is answering a question nobody asked. Measured on
> #8732, which names PR #8517 only in passing: on `main` the described silent miscompilation is
> a loud validation error, none of the symbols it blames exist, and the honest reading is "not
> reachable from here", not "does not reproduce". Read the thread for a branch or PR reference
> and grep ground truth for the symbols the report names *first*; if they are absent, say so as
> the headline rather than reporting the absence of the symptom. `inconclusive` with
> `needs-human-judgement` is the right verdict, and the write-up has to explain that it is
> unmeasurable rather than fixed.

> **Sometimes `repros` is the uninteresting half of the answer.** #2427's command line still
> fails exactly as filed — but the thread had already established in 2019 that this is the
> platform's argv splitting, before dxc sees anything, and that FXC does the same. Reporting
> "confirmed, still broken" would have been true and actively misleading. The finding was that
> the *agreed fix* had lapsed: no directory-taking flag was ever added, and the PR carrying it
> (`Fixes #2427`) was closed unmerged by an inactivity sweep six weeks before this triage. When
> a thread has already diagnosed the behaviour, re-confirming it adds nothing; check what
> happened to the resolution instead — the linked PRs, the planned doc change, the proposed
> flag. `gh api repos/<repo>/issues/<N>/timeline` lists every cross-reference.

> **Not every repro is a shader.** Command-line, build-system and API issues are still
> triageable, but `cmd.txt` assumes one dxc invocation over HLSL, and a shell will rewrite the
> very thing under test. #2427 had to be driven through `cmd.exe` verbatim, because PowerShell
> re-quotes arguments and silently repairs the bug. Keep the raw invocation in its own script
> next to the issue, and record which shell produced the result.

> **PowerShell will silently eat `$` and `` ` `` out of any prose you write through it.** Two
> different mechanisms, both invisible, both measured in batch 006 and both landing in committed
> artifacts. In a **double-quoted** string `$Globals` expands to nothing — `triage.py verdict
> --summary "... not $Globals-specific ..."` recorded *"not -specific"*, and that sentence then
> propagated into `overview.md`. In the same string `` `else `` becomes `U+001B` + `lse`,
> because `` `e `` is PowerShell's escape character; that one reached
> `3251/manual-case-assert-stack.txt` and **cannot be corrected**, because hand-editing a
> committed capture is falsification. **Single-quote any string containing `$` or a backtick**,
> and prefer writing prose into files with an editor rather than through the shell. Note the
> converse: `U+001B` in a *captured* file is usually legitimate — Compiler Explorer returns
> ANSI-coloured Clang output — so do not "clean" it.

**Judge a `does-not-repro` against the configuration the reporter used.** A Debug build is the
right ground truth for asserts, but it is the *wrong* one for issues the reporter says only
fail in Release. Where the report is configuration-dependent or non-deterministic, test the
release binaries and repeat the run; a single clean pass is not evidence of a fix. Prefer
`inconclusive` over an unearned `does-not-repro`.

> **A nondeterministic bug makes single-run probes worthless — use `--repeat`.**
>
> ```bash
> python triage.py run    --issue <N> --repeat 25
> python triage.py bisect --issue <N> --repeat 10 --linear
> ```
>
> `--repeat` runs the repro up to N times and reports the symptom if *any* run shows it,
> short-circuiting on the first sighting so a reproducing release stays cheap.
>
> Measured on #3768, whose heap corruption fires on 70–82% of runs in the affected releases
> (33/40 at v1.6.2104, 28/40 at v1.6.2106, counted in `issues/3768/`'s repeated-run capture):
> a one-shot probe calls a *reproducing* release clean roughly a quarter of the time. During a
> linear scan that does not just add noise, it **invents release boundaries that do not
> exist** — an unlucky probe looks exactly like a fix.
>
> Repeats are also what converts a clean result into evidence. Absence of a crash means
> nothing until you know the per-run hit rate: at ~70%, thirty consecutive clean runs has
> probability ~2e-15, so it is a real finding rather than an absence of one. Measure the rate
> on a known-bad release first, then quote it.
>
> **A rate you quote must be countable from a file in the issue directory.** #3768's draft
> carried "68–82%" for three batches with no capture behind it: the aggregate lived only in
> the database, a `reindex` discarded it, and the figure became unfalsifiable — provably so,
> since the committed `notes.md` said 110 clean runs where `verdict.json` said 105 and nothing
> on disk could settle which was right. Re-measuring gave 70–82%, close enough that nobody
> would have caught the drift by eye. `run --repeat` now stamps the rate into the capture
> header, but a hand-run matrix must be written out as `manual-case-*.txt` with every attempt's
> command and exit status, and the draft must cite counts (`33/40`) rather than a percentage
> a reader cannot re-derive.
>
> Reach for it whenever the reporter says "intermittent", "sometimes", "flaky", or names heap
> corruption, uninitialised memory, ASLR or threading. Do not use it as a blanket default —
> it multiplies the cost of every probe.

### 6. Locate the transition

```bash
python triage.py bisect --issue <N>
python triage.py bisect --issue <N> --linear    # non-monotonic history
python triage.py bisect --issue <N> --repeat 10 # nondeterministic symptom
```

Checks both endpoints first and short-circuits when they agree, so an always-broken or
never-implemented issue costs only two runs. Reports `fixed-in <tag>`, `regressed-in <tag>`,
`always-repro'd`, or `never-repro'd-in-releases`. Releases download lazily and are cached
across issues.

> **A probe only counts if that release actually compiled the repro.** A release that predates
> the target profile, or that lacks the feature entirely, rejects the input without ever
> reaching the code under test — and fails in a way no symptom predicate matches, so it scores
> as `no-repro` and **fakes a regression**. The runner classifies these as `invalid-probe`;
> `bisect` trims them off the ends of the range and reports how many it skipped.
>
> Measured on #3873: every release up to v1.6.2112 "fixed" it purely because its repro targeted
> `ps_6_7`, which did not exist yet — `error: invalid profile ps_6_7`. Retested at `ps_6_0`,
> the oldest release hangs, so it had in fact always reproduced. On #3768 the same trap wore a
> different face: v1.4.1907 answers `SPIR-V CodeGen not available`.
>
> **Prevention:** target the repro at the oldest profile and flag set that still shows the
> symptom, not the newest one the reporter happened to use.

> **The same trap fires one level up, in the front end.** A release predating a language
> *feature* — a type, an intrinsic, an attribute — rejects the repro with an ordinary semantic
> diagnostic, not a profile error. Measured on #3038: v1.4.1907 answers `use of undeclared
> identifier 'RayQuery'` because DXR 1.1 did not exist yet. Scored as a clean run, that turns
> "always reproduced as far back as is checkable" into a spurious "regressed in v1.5.2010".
> `invalid-probe` detection therefore also matches `use of undeclared identifier`,
> `unknown type name`, `no member named` and `no matching function for call to`.
>
> Every marker has to name something the compiler does not **have**. A bare `is not supported`
> does not: DXC emits that phrase from about 25 distinct diagnostics about present-day code
> (`operator is not supported`, `signed integer division is not supported on
> minimum-precision types`, PR #8517's own `mixing bound and descriptor heap resources … is
> not supported`), so unqualified it demotes ordinary errors. It is now anchored to the
> target/profile/shader-model forms. Noticed on #8732. If you add a marker, add it because you
> watched it fire on a release that genuinely predated the feature — guessing silently discards
> evidence.

> **The markers break down on an issue whose reported symptom IS a diagnostic**, because then
> the signal ("this build rejected the input before reaching the code under test") and the
> symptom (an error message) are the same observation. Batch 004 predicted it; #3055 measured
> it in both directions.
>
> * A release emitting the **good** diagnostic the issue asks for scores `no-repro` — which is
>   exactly what "fixed here" looks like for a diagnostic-quality issue — and was demoted, so
>   `bisect` trimmed away the very release that fixed it.
> * A probe that **matches** was demoted whenever the predicate carried any absence clause, so
>   every release including ground truth would have been discarded and `bisect` would have
>   reported "no release could run this repro; retarget it at a profile/flag set the releases
>   support" — a message that misattributes the cause entirely.
>
> `classify` now suppresses the demotion when a *positive* clause of the issue's own
> `match.json` quotes the matched marker verbatim. That is the narrowest rule that fixes both,
> and it requires a human to have written the diagnostic in as the symptom. Nothing else is
> loosened: inverted clauses do not count, no predicate is evaluated as a regex against the
> marker, and the converse rule — "any marker on a matching probe means a bad probe" — stays
> rejected, because #1627's reported symptom *is* an `unrecognized argument` diagnostic.
>
> **What this means for you when triaging a diagnostic-quality issue:** write the diagnostic
> text into `match.json` rather than approximating it, and check the header. Every demotion now
> stamps `# invalid-probe-reason:` into the capture saying which rule fired and on what text,
> so an `invalid-probe` you did not expect is readable on disk instead of only reconstructable
> by re-reading `classify`.

> **`invalid-probe` on the repro is ambiguous on its own; a feature-presence control resolves
> it.** "This release rejected the input" can mean the release predates the feature, or that
> something unrelated in the repro was rejected — and only the first justifies trimming the
> release out of the history. Run the *smallest shader that uses the feature at all* under the
> same profile and flags. `invalid-probe` on both means feature absence. `invalid-probe` on the
> repro with a **clean** control means the rejection is about your repro, and silently trimming
> it would hide a real result. Measured on #8725, whose brief predicted history would be
> unmeasurable because `lib_6_9` is new: five of twenty releases can express it, a
> `control-hello.hlsl` proved so, and all five reproduce — a full history where the prediction
> said there would be none.

> **An absence-based predicate is satisfied for free by a compile that never got started.**
> If the symptom is that something is *missing* (`not_contains`, `not_regex`, or an inverted
> `contains`), then any release that fails to parse the repro emits no match either — and
> scores as a textbook reproduction. #1877's predicate is `not_contains fptosi`; a release that
> rejected the input would have "reproduced" it perfectly. The runner demotes such a probe to
> `invalid-probe` **only** when the output also tripped a feature-absence marker or the run
> failed internally. **An ordinary diagnosed error is neither** — on Windows that is E_FAIL
> plus an `error:` line, which is the likeliest early failure across a twenty-release history,
> and it still scores `repro`. Measured on #2792 against real captured output: a probe with
> three `error:` lines and no DXIL scored as a reproduction under an unanchored absence
> predicate. Demoting that case is not available, because an issue whose symptom is a *wrong*
> diagnostic legitimately errors on every reproducing probe (that is #3055's defect in a new
> shape), so **the runner warns instead** when an absence-only predicate matches a failed
> compile. Anchor the predicate with a positive clause — #2792's
> `extractvalue %dx.types.CBufRet.f32 <v>, 1` cannot be emitted by a compile that failed — and
> always confirm the probe actually emitted DXIL.
>
> **The same clause is also vacuously true on a shader that never mentions the symbol**, and no
> amount of tooling can see that. #8732's `not_regex "%bound\w*\s*=\s*Op\w*Variable"` was
> satisfied for free by a case whose shader declares no bound resource at all: the compile
> succeeded, the predicate matched, and the probe measured nothing. Only a control caught it —
> `run --expect no-match` printing `WARNING: control expected no-match but scored repro`. If an
> absence clause names a specific symbol, one of your controls must be a shader that *does*
> declare it.

> **A crashed probe measured nothing.** A release that access-violates on the repro did not
> observe the reported symptom; it failed before it could. Scored as `no-repro` that is the
> most dangerous direction of error — it erases a defect at exactly the release boundary
> someone will act on. Measured on #2202: v1.8.2403 answers
> `Internal compiler error: access violation` and a `--linear` scan duly reported a fix window
> that does not exist. Now classified `invalid-probe`, unless the crash *is* what the predicate
> is looking for.

> **The feature-absence trap also runs forwards in time.** Every marker above means "you used
> something that does not exist yet"; the mirror image is a *newer* compiler rejecting an
> *older* repro because a default moved under it. Measured on #2202, filed in 2019 with no
> `-HV`: at today's default `-HV 2021` the front end rejects `bool3 ? a : b` before codegen, so
> the validator the issue is about never runs and the bug looks fixed on `main`. **Pin the
> language version of any repro older than the current default**, and treat "reproduces on
> every old release but not on `main`" as a claim to check rather than a fix to celebrate.

> **`never-repro'd-in-releases` is only a finding if a release could have shown the symptom.**
> An assert-only defect cannot appear in a release build at all: `assert.h` compiles asserts
> out under `NDEBUG`, so 20 clean releases are a property of the build configuration, not of
> the code. Measured on #2191, where the ground-truth Debug build exits `0xE0000001` and every
> release exits 0 with correct DXIL. `bisect` now warns when those two facts coincide. Say
> "silent by construction", not "fixed", and do not suggest closing.
>
> **The converse is just as common, and this warning primes you to miss it.** An assert can be
> Debug-only while the *defect* is not: with the check compiled out, the unchecked value flows
> on and the release build crashes anyway. Measured on #3259, where `DXASSERT_NOMSG(Ty)` becomes
> `do { } while (0)` under `NDEBUG` (`include/dxc/Support/Global.h:369`) and the null type
> reaches `Builder.CreateAlloca` two lines later — so all 19 probeable releases access-violate
> and the history is fully meaningful. The discriminator is cheap and you should always run it
> before writing "silent by construction": find the assert macro's `NDEBUG` expansion, then read
> what the unchecked value does next.

> **Binary search assumes the symptom is monotonic. Fix-then-revert issues are not.** With a
> non-monotonic history, binary search returns an arbitrary boundary — and when both endpoints
> agree it short-circuits to "never reproduced", missing a real window entirely. Use `--linear`
> whenever the issue history mentions a fix, a revert, or a re-opening. It costs one run per
> release, but every release is cached after the first issue that needs it.
>
> Measured on #3768: clean → **broken in v1.6.2104 and v1.6.2106** → clean from v1.6.2112. A
> binary search sees a clean v1.5.2010 and a clean v1.9.2607 and concludes the bug never
> existed. The linear scan found the two-release window, which matched the report date and
> turned the issue into the batch's one closable result.
>
> `--linear` and `--repeat` compose, and on #3768 both were needed: the scan has to visit every
> release *and* probe each one enough times, or an unlucky run inside the broken window closes
> it prematurely and reports a one-release blip.

**The bisection floor is v1.4.1907 (2019-07)** — the oldest release shipping a usable `dxc`.
For issues predating it, `always-repro'd` means "for as long as it is possible to check", and
must be reported that way rather than as "since it was filed". For SPIR-V issues the floor is
higher still, since v1.4.1907 has no SPIR-V codegen.

### 7. Publish a shareable repro

```bash
python triage.py godbolt --issue <N>
```

Compiles the repro on [Compiler Explorer](https://godbolt.org), prints the result per
compiler, and stores a short link on the issue row. Default compilers are `dxc_1_6_2112`
(CE's oldest) and `dxc_trunk`. **The link is verified before it is handed over** — never
publish one without checking it shows what you claim.

**Always write `issues/<nnnn>/godbolt-note.txt`.** It is prepended to the shared source as a
`// What to look for` banner. A bare link to a shader that compiles "fine" invites the reader
to conclude the bug is gone — name the exact thing to check: the `HLSL Bind` column, the empty
`main()`, the abnormal exit code. Keep it in its own file rather than in `repro.hlsl`, so the
repro stays exactly what was tested locally; the banner is presentation, not evidence.

**Not every issue deserves a link.** If the whole behaviour is a one-line error, or the issue
is a pure feature request with nothing to see, record that decision instead of forcing one:

```bash
python triage.py godbolt --issue <N> --skip "pure feature request; nothing to see"
```

But revisit that call once you have tried a Clang pane. #1627 was skipped as "just an
unknown-argument error" — until Clang turned out to *have* the capability, reachable as
`-Xclang -include`, which reframed the request from "add a feature" to "expose an existing one
at the driver level". A comparison can create something worth seeing where there was nothing.

Use `--compilers` for anything more interesting; the spec is saved to the issue's
`godbolt.txt` and reused afterwards. `id:<args>` overrides the arguments for one compiler,
which is how a contrasting compiler is placed beside DXC:

```bash
# "FXC diagnoses this and DXC does not" — shown, not asserted
python triage.py godbolt --issue 1306 \
  --compilers "fxc_10_0_19041:/T cs_5_0 /E main,dxc_1_6_2112,dxc_trunk"
```

A link that makes the bug *visible* beats one that merely reproduces it. For wrong-code
issues, point at the evidence in the DXIL; output filters are deliberately configured to keep
DXC's comment-based tables, which CE strips by default.

**Consider adding a Clang pane.** CE carries `hlsl_clang_trunk` and
`hlsl_clang_assertions_trunk`. Because HLSL support is being rebuilt in Clang, "does this still
reproduce in DXC?" and "has the successor compiler already answered this?" are different
questions, and the second is often the more useful one for an old issue:

```bash
python triage.py godbolt --issue 708 \
  --compilers "dxc_1_6_2112,dxc_trunk,hlsl_clang_trunk"
```

Worth doing when the issue is a missing diagnostic, an FXC/DXC disagreement, a language-design
question, or is labelled `check-in-clang`. Clang may reject what DXC accepts (which answers an
open design question), or share the gap (which shows it is still live in the new front end).
The two Clang builds usually agree; prefer one pane unless they differ.

**When Clang cannot compile the repro's shader stage, translate it — or omit the pane.**
Clang's stage support is uneven: compute is complete, pixel parses but the backend cannot lower
any shader writing `SV_Target`, vertex parses but the backend cannot lower signature I/O either
(`Unsupported intrinsic llvm.dx.load.input.v4f32`, measured on #2528), and geometry is not
supported at all. A pane full of errors
about the stage says nothing about the issue, so:

1. **Prefer a compute-shader translation.** If the construct under test is not stage-specific,
   restate it as a `[numthreads]` entry point writing to an `RWBuffer`. All three compilers
   then answer the same question on the same input. This is usually *stronger* evidence, not a
   compromise — #1702's compute variant made DXC emit `float undef` stores that its own
   validator rejects, where the pixel version merely produced an empty `main`.
2. **Otherwise omit the pane.** #1768 is inherently GS-specific (`PointStream`,
   `maxvertexcount`) and its construct compiles cleanly as a compute shader in both compilers,
   confirming a translation would exercise a different path and mislead.

**A missing Clang repro is better than a noisy, useless one.** Check the translation still
reproduces before adopting it, and keep the stage-accurate original as the local evidence.

> **A Clang error is not evidence until you have a control.** Clang's DXIL backend is
> incomplete, so it fails on inputs that have nothing to do with the issue. #1702 looked like
> Clang diagnosed it — `Unsupported intrinsic llvm.dx.store.output.v4f32 for DXIL lowering` —
> until a one-line `float4 main() : SV_Target { return 0; }` produced the *same* error.
> **Before believing any cross-compiler difference, compile something trivial with the same
> flags and confirm the difference does not survive.** Where the backend is the blocker,
> `-fsyntax-only` asks the narrower question the front end can still answer.
>
> **Reach for `-fsyntax-only` first whenever the symptom is a front-end diagnostic**, but only
> when you need to: the rule is whether the front end *hard-errors*. If it does, the backend
> never runs and the pane is already clean — #3055's Clang pane needs no `-fsyntax-only`
> because `no matching member function for call to 'Sample'` is a Sema error. If the symptom is
> only a warning or a note, the compile proceeds into a backend that cannot lower `SV_Target`,
> and the pane fills with noise about the stage — which is why #2530's pane needs it. Two
> workers in one batch reached opposite-looking conclusions here; this is the rule that
> reconciles them.
>
> **FXC panes need controls too.** The control discipline above is written about Clang, but an
> FXC pane is a different compiler with its own failure modes and the same reasoning applies.
> Also note that `godbolt` records only the **first line** of each pane's output in its summary:
> for `hlsl_clang_trunk` that is usually a `-Qembed_debug` unused-argument warning, so the tool
> can print nothing of the finding while the link itself is perfect. Open the link.

The same discipline applies to argument handling: `dxc_trunk` appears to accept `/FI` silently,
but so does `/ZZZNONSENSE` — on CE's Linux builds a `/`-prefixed argument looks like a path, so
MSVC-style flags are not testable there at all.

Three limits, all of which bound how much the link can be trusted:

| Limit | Consequence |
| --- | --- |
| CE runs **Release** builds | Debug-only asserts look clean. CE corroborates the local build, never overrules it |
| CE's oldest DXC is **1.6.2112** | Cannot date a fix older than that; use `bisect` for history |
| CE is **single-file** | Multi-file repros are partial at best; say so in the notes |

> **Do not fold a multi-file repro into one file without a control.** The obvious device for
> #8527 — a header that includes *itself* under a different spelling — appears to reproduce the
> `#pragma once` failure. It does not: the same construction with a *matching* spelling fails
> identically, because clang ignores `#pragma once` in the main file. The fold measured a
> different rule. **Whenever a repro is transformed to fit CE, run the transformation on a case
> that is known-good and confirm it still passes.** If it does not, the transformation is the
> subject and the issue is not.

> **When CE cannot show the symptom at all, say so in the comment.** #2191 is a Debug-only
> assert and CE ships no assertions-enabled DXC, so the link shows three compilers succeeding.
> Published bare, that reads as "cannot reproduce". It is still worth publishing — it is the
> evidence that release builds are unaffected — but only with the limitation stated beside it.

`dxc_trunk` is a rolling build and is not reproducible over time. It can even vary between
runs of the same input — #1768 alternates between `SIGSEGV` and a bad-cast error. Do not pin
an exact trunk symptom in anything you publish; describe the class of failure instead.

### 8. Review the labels

```bash
python triage.py labels --refresh          # re-fetch the taxonomy, then list it
python triage.py labels --issue <N>        # current vs proposed for one issue
```

**Never hardcode a label list, and never work from memory or from a previous batch.** Labels
get added, renamed and retired; the taxonomy is repo state. `labels` re-fetches it, warns when
the cache is over a day old, and flags labels on an issue that no longer exist.

Proposals are recorded through `verdict` and **validated against the live set** — an unknown
label is rejected with a near-miss suggestion rather than silently stored:

```bash
python triage.py verdict --issue 1702 \
  --labels-now "bug,shader-linking" \
  --labels-add "fxc-disagrees,incorrect-code,correctness,check-in-clang" \
  --labels-remove "shader-linking"
```

What to look for, having just established what the issue actually does:

- **Severity that the triage contradicts.** A crash labelled only `bug` understates it.
- **Labels the evidence does not support.** Removals need a reason from the issue itself, not
  a hunch — check the body and every comment before proposing one, and say in the draft that
  you may be missing history.
- **Labels that record the *finding*,** e.g. an FXC/DXC difference, or "the fix belongs in
  Clang". These are the ones that make the backlog searchable later.
- **Missing routing labels** on issues that are really feature requests.

Read the label *descriptions*, not just the names — several are narrower than they sound. For
example `validation` means **DXIL validation** specifically, not "the compiler should validate
this"; a request for a compile-time diagnostic is mislabelled by it.

Recorded, **never applied**.

### 9. Draft the issue comment

Write `issues/<nnnn>/comment.md` — what a maintainer could post, ready to use. Open it with
a **rendered** warning callout, not an HTML comment: these files are committed and browsable
on github.com, where `<!-- ... -->` is invisible to exactly the audience that most needs to
know a draft is a draft.

```markdown
> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#1803](https://github.com/microsoft/DirectXShaderCompiler/issues/1803).
```

Name the issue, so a file found on its own is traceable. Claim only what the file can know:
"unposted" is not verifiable by a file that outlives its own posting.

- Lead with the verdict and the version tested (`still reproduces on main (…, <sha>)`).
- Show the evidence: the annotated link, and the two or three lines of output that matter.
- Say what changed since the report if the symptom has moved — that is often the single most
  useful thing in the comment.
- Close with the label suggestion and its one-line justification.
- Where the next step is a product or language decision, say so; do not pre-empt it, and
  never promise a fix or a timeline.
- Quote compiler output **verbatim and verified**, not from memory. Re-run it.
- **Be concise.** Do not restate what the code block or the linked page already shows. Cut
  hedging, preamble, and any sentence that survives only to introduce the next one.

**End every draft with the AI-assistance disclosure.** These comments land on other people's
issues, and a reader is entitled to know how the evidence was produced — not least because it
tells them what kind of mistake to look for. Use a consistent trailer, separated by a rule:

```markdown
---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
```

Keep it short and factual. It is a provenance note, not an apology or a disclaimer — do not
hedge the findings themselves, which are verified by running the compiler. The invitation to
flag errors is the useful part: it is what turns disclosure into something the reader can act
on.

These are drafts for a human to review and post. **Posting them is not part of this skill.**

### 10. Have a different model review the drafts

**Required, not optional.** Before the drafts go anywhere near a human reviewer, hand them to
a separate agent running a *different* model. The author of a draft is the worst judge of its
length: you already know why every sentence is there, so the redundant ones still read as
necessary.

Send the reviewer:

- the paths to every `comment.md` in the batch, and the `notes.md` files as background;
- who the audience is — maintainers plus original reporters, on a public repo, some threads
  years old;
- that **concision is the primary criterion**, and that the goal is subtraction: it must not
  propose new sections or new information;
- what is off-limits to cut — the specific technical evidence (error codes, version numbers,
  symbol and file names, IR snippets) and any finding that the issue text is stale;
- a demand for quoted current text plus exact replacement text, not general advice.

Then **apply the review with judgement, not wholesale**. In practice it is reliably right
about verbosity and about unsupported claims, and unreliable about domain specifics — expect
it to propose reverting a correction it lacks the context for, and to flag genuine hedging that
is actually deserved caution. Two categories worth accepting almost every time:

- **Speculative root-cause or effort claims.** "Suggests memory corruption", "looks cheap",
  "was probably a development-branch symptom". State the observation and the limits of what
  was tested; drop the diagnosis.
- **Adverbs the evidence no longer supports.** "Silently" is wrong the moment the compiler
  emits any warning at all.

Where you reject a suggestion, know why. Record anything that changes the method in the batch
report, and record the reviewer itself with `verdict --reviewed-by <model>` — a required step
that leaves no trace is one you cannot later tell was skipped.

**Re-run the review when a draft changes materially.** A draft rewritten after new evidence has
not been reviewed, and the second pass finds different things than the first. Brief the reviewer
with the *current* evidence — it flags anything absent from its brief as unsupported, so an
under-briefed reviewer generates false positives against claims you have in fact verified. Two
recurring classes worth accepting:

- **Scope creep in claims about history.** "Gone from every release" when only v1.4.1907 onward
  was tested; "unchanged since 2019" when the endpoints, not every release, were checked.
- **Rhetorical flourishes.** A comment landing on a stranger's multi-year-old issue should read
  as a report, not an argument. Keep the finding, drop the point-scoring.

And two it gets wrong often enough to check: it will paraphrase away literal diagnostic text
(`error X3072: ...`) that people actually search for, and it will read a caveat aimed at future
triagers as an accusation against past ones. It also tends to cut *actionable* caveats — the
one remaining test that would settle a verdict, or a warning about a trap that has already
produced a wrong answer once. Those earn their space; cut the epistemics around them instead.

A third pattern, seen in batch 002: it is good at catching claims that are subtly **wrong about
what correct behaviour would be**. "No release has ever compiled this correctly" is wrong when
the input is invalid and *should* be rejected; "only DXC fails to say so" is wrong when DXC does
emit an error, just a bad one. These read fine until someone who knows the compiler reads them.

**Check the review in both directions: it can introduce an error while removing one.** Batch 003
tightened #2427 to "Through `cmd.exe`, the trailing backslash escapes the closing quote" — but
the escaping is CRT and shell argv splitting generally, not a `cmd.exe` quirk; `cmd.exe` was
only the harness that reproduced it faithfully. Concision pressure pulls toward attributing a
general behaviour to whatever specific thing the sentence already mentions. Re-read every
accepted rewrite against the evidence, not just against the original wording.

**Its most valuable output is not the cuts. It is the arithmetic.** A concision reviewer reads
every claim looking for words to remove, which makes it check quantifiers and counts that a
domain reader skims. In batch 004 it caught three factual errors that no amount of domain
expertise would have surfaced: "the third error" where the file has four; "every release back
to v1.4.1907" where `bisect` short-circuited after two endpoints; "with other atomics" where
exactly one other atomic was tried. **Give it the evidence files, not just the drafts** — it
cannot check a count it cannot see, and these are the corrections worth the whole exercise.
Treat any bare numeral or universal quantifier it queries as guilty until re-counted.

Under the parallel model the reviewer is also the **only** reader who sees all five drafts, so
it is the first place a house style can be enforced. Note what it cannot do: it does not know
that two issues are related, because nothing in a draft says so. Cross-issue claims are
collation's job and must be settled before the review, not after.

### 11. Write it up

Create `issues/<nnnn>/notes.md` — what was tested, what happened, on which compilers, and the
assessment. Corroborate from source where you can: showing that a field is parsed but never
read is far stronger evidence than an output observation. Then record the verdict:

> **A negative result from a command that errored is not a negative result.** Attributing
> #3038's fix to a PR, `git merge-base --is-ancestor <sha> origin/release-1.8.2505` exited
> non-zero and was briefly read as "the fix is not in that release" — refuting the hypothesis.
> In fact the ref did not exist locally, because the release branches had never been fetched.
> The command was answering a different question. Once fetched, the ancestry check confirmed
> the opposite. Before believing a negative, check that every input to it resolved: that the
> ref exists, the file was found, the flag was parsed. This is the same failure as the
> `invalid-probe` trap, one layer out — a tool that never ran the test still returns something
> that looks like an answer.

> **When attributing a fix to a specific change, state the size of the window.** A verified
> ancestry check proves a commit is *in* the fixing release, not that it *is* the fix. #3038's
> window between v1.8.2502 and v1.8.2505 holds 162 commits. Say so, and call the attribution
> strong rather than certain unless you built at the commit and tested it.

```bash
python triage.py verdict --issue <N> --status repros --repro-quality complete \
  --history "always-repro'd" --confidence high --suggested-action still-valid-keep-open \
  --summary "..." --notes-path issues/<nnnn>/notes.md --triaged-with-commit <sha> \
  --triaged-by "<model>" --reviewed-by "<reviewer model>"
```

Add `--text-stale "<what is stale>"` whenever the issue's own text no longer describes
what the compiler does. That means the title, the body, **or a maintainer comment left
standing in the thread** — the harm is identical in all three cases, because a reader
spot-checking the issue believes the text over the compiler. #3055 is the third shape: the
body is accurate, but a 2023-07-14 comment says "compiles successfully now" and the body was
then edited on 2023-09-27, so a reader going top-down meets a maintainer closing the question
above a report that still reproduces. Say which of the three it is.
Record it here rather than only in `notes.md`: it is the finding a
maintainer can act on immediately, and `overview.md` sorts it to the top of its tier and
quotes the text. A finding left in prose reaches nobody who is not already reading that issue.

`--triaged-with-commit` records which compiler was measured; `--triaged-by` and
`--reviewed-by` record who did the measuring and who checked the write-up. Record all three.
A verdict is weighed differently depending on which model produced it, and step 10's review is
mandatory but unfalsifiable if nothing on disk says it happened — an empty `reviewed_by` is
the only way a skipped review is visible later.

Suggested actions (recorded, **never applied**): `close-fixed`,
`needs-repro-from-reporter`, `still-valid-keep-open`, `needs-human-judgement`,
`duplicate-of #N`, `enhancement-not-bug`.

## Batch report

Write `reports/batch-NNN.md` covering: ground truth used (commit + version), a summary table
with a Compiler Explorer link per issue, per-issue findings, the **draft comments**, and —
importantly — **what the batch taught you about the method**. Predicate bugs and methodology
gaps found while triaging are as valuable as the verdicts, and should change how the next
batch is run.

Splice the drafts in from their source files rather than copying them, so the report and the
artifacts cannot drift:

```bash
python scripts/render_comments.py <batch>     # e.g. 002
```

Re-run it after **every** edit to a `comment.md`.

Flag prominently any issue whose **text no longer matches its behaviour**, and record it with
`verdict --text-stale "<what is stale>"` so it reaches the cross-batch overview instead of
living only in this report's prose. These are the highest-value findings: the defect is real,
but anyone spot-checking against the description will wrongly conclude "cannot reproduce".
This includes the **title**: #3444 has claimed since 2021 that `float2`/`float3`/`float4`
work, and none of them do.

> **`text_stale` is a claim about the reporter's writing — hold it to a high bar.** It says
> "this description is now wrong", so it lands differently from every other verdict field.
> Two failure modes, both hit on #8737:
>
> *Applied to an issue that is not stale at all.* #8737 was filed **three days** before it
> was triaged, by a reporter who had already documented both symptoms precisely. Its title,
> "silent UB or ICE", is exactly what the compiler does. It was nonetheless marked stale as
> "understates it" — turning a nuance into a defect claim about someone's writing. **Check
> the filing date first:** a recently-filed issue's text is almost never stale, and
> "understates it" is not staleness. Retracted.
>
> *A summary that falsifies the analysis it summarises.* The draft correctly said
> `atomicBinOp` has **no** sample-index operand. The one-line `text_stale` compressed that to
> "`i32 undef` where the sample index belongs" — asserting the slot exists. The reporter
> quoted that phrase back and corrected it. A short field is not licence to state something
> the long-form evidence does not; **compression must only remove claims, never add one.**

Always state the sampling bias. Verdicts from the oldest issues do not generalise to the
backlog.

## Cross-batch overview

`reports/overview.md` is the standing answer to "what should we do next?" across every issue
triaged so far. **Regenerate it at the end of every batch — it is the last step:**

```bash
python scripts/triage.py reindex        # rebuild the db from the evidence
python scripts/render_overview.py       # then regenerate the overview
```

It is generated entirely from `triage.db`, which `reindex` rebuilds from the committed
`verdict.json` files, so it cannot drift from the evidence and **must never be hand-edited**.
If a row is wrong, fix the verdict and re-run; an edit made in the file is lost on the next
batch and, worse, silently disagrees with the artifacts until then.

Ordering is by **what action is available**, not by severity — the two come apart, and
severity is already in the issue's labels. An always-reproducing crash is worse than a stale
title but needs no decision: it is open, labelled, and waiting on a fix rather than on triage.
So `close-fixed` sorts first, `needs-human-judgement` second, and `still-valid-keep-open` last,
because its triage conclusion is "nothing to do here". Within a tier, issues carrying a
proposed title or label change sort above those with none, for the same reason.

Adding a new suggested action means adding it to `TIERS` in `render_overview.py`; anything
unrecognised falls through to the last tier rather than disappearing.

## Useful queries

```bash
python triage.py status
python triage.py sql "SELECT number, status, history FROM issues WHERE status='does-not-repro'"
python triage.py sql "SELECT number, fixed_in FROM issues WHERE history='fixed'"
```

## Selecting a batch

```bash
gh issue list --repo microsoft/DirectXShaderCompiler --state open --limit 20 \
  --search "sort:created-asc" --json number,title,createdAt,labels
```

Mix the batch deliberately — an all-oldest batch is unrepresentative and may not exercise
bisection at all. Include `crash`, `spirv`, and mid-age issues so the workflow is tested where
"no longer reproduces" is actually plausible.
