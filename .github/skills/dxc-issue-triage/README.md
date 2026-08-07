# DXC issue triage

Tooling and accumulated evidence for answering, per open DXC issue: **is there a usable
repro, does it still reproduce, and when did that change?**

`SKILL.md` is the procedure. This file describes what is stored here and how to pick it up.

## Layout

```
scripts/            triage.py, test_predicates.py, render_comments.py,
                    render_overview.py
data/issues/<nnnn>/ the evidence for one issue
data/reports/       overview.md, plus one report per batch
.cache/             compilers and the database -- gitignored, regenerable
```

Everything under `data/` is committed. That is the point: a verdict nobody can re-check is
just an assertion, and these verdicts are the input to closing or keeping issues open.

## Start here: `data/reports/overview.md`

Every issue triaged so far, **ordered by what a maintainer can act on** — closable first,
then decisions that are blocked on a person, and confirmed-still-broken last. It links each
issue to its draft comment, notes and Compiler Explorer repro.

It is **generated**, never hand-edited:

```bash
python scripts/triage.py reindex        # db <- committed verdict.json files
python scripts/render_overview.py       # overview.md <- db
```

Both run at the end of a batch. `triage.py audit` fails if `overview.md` is older than the
newest `verdict.json`, so a forgotten regeneration is caught rather than shipped — a stale
overview is a well-formed document that quietly omits a whole batch, which is exactly the
kind of error nobody notices.

Ordering is by available action, not severity. The two come apart: an always-reproducing
crash is worse than a stale title, but it is already open and labelled and is waiting on a
fix, not on triage. Severity lives in the issue's labels; this report answers "what next?".

## Files in an issue directory

| file | what it is |
| --- | --- |
| `expected.md` | what "this reproduces" means, **written before anything was run** |
| `repro.hlsl`, `cmd.txt` | the repro, and the exact arguments every compiler receives |
| `cmd-as-filed.txt` | present when `cmd.txt` deliberately departs from the report |
| `match.json` | the symptom predicate, with a `note` justifying it |
| `out-<compiler>.txt` | a probe of the repro; header records exe, command, exit and verdict |
| `variant-*.txt` | a *control* or translated variant — deliberately not scored by `match.json` |
| `manual-case-*.txt` | output captured by hand, where the repro is not a `dxc` invocation |
| `notes.md` | what was tested, what happened, and the assessment |
| `comment.md` | a **draft** comment for a maintainer to review — never posted by this skill |
| `verdict.json` | the recorded verdict; the database is rebuilt from these |
| `issue.json` | the issue as it read at triage time |

`issue.json` is kept deliberately. A recurring and high-value finding is that an issue's
text no longer matches its behaviour, and issues get edited — so a snapshot of what it said
when it was measured is part of the evidence.

## Reading a verdict

`verdict.json` is terse by design. The vocabulary it uses:

| `status` | meaning |
| --- | --- |
| `repros` | the reported symptom is still observed |
| `does-not-repro` | the repro runs clean; the symptom is gone |
| `changed-behavior` | still misbehaves, but differently than reported |
| `not-compiler-verifiable` | judging it needs a GPU, driver or runtime, not a compiler |
| `inconclusive` | the repro is too ambiguous to judge |

| `repro_quality` | meaning |
| --- | --- |
| `complete` | the issue supplied something that runs as-is |
| `partial` | supplied, but had to be completed |
| `prose-only` | described in words, no code |
| `none` | nothing to work from |
| `agent-constructed` | built during triage; treat conclusions accordingly |

`history` is either `always-repro'd`, `never-repro'd-in-releases`, or names the release on
each side of a transition. **The floor is v1.4.1907** — the oldest release shipping a usable
`dxc` — so `always-repro'd` means "for as long as it is possible to check", not "since it was
filed".

`text_stale` is set when the issue's own text — title, body, or a maintainer comment left
standing in the thread — no longer describes what the compiler
does — #3444 has claimed since 2021 that `float2`/`float3`/`float4` work, and none of them
do. It is a field rather than a remark in `notes.md` because it is the class of finding that
most needs to surface: the defect is real, but anyone spot-checking the issue against its own
description concludes "cannot reproduce". `overview.md` sorts these to the top of their tier,
since editing a title is an action available immediately on an otherwise unactionable issue.
The comment case is the same defect wearing different clothes: on #3055 the body is accurate,
but a 2023 comment saying “compiles successfully now” sits above it and the body was edited
afterwards, so a reader going top-down is told the opposite of the truth by the issue itself.

In an `out-*.txt` header, `# verdict:` is per-probe, not per-issue, and has two further
values: `invalid-probe` means that compiler never actually ran the repro — it rejected the
profile, a flag, or a language feature that did not exist yet; or it crashed before reaching
the code under test — so it is evidence of nothing and is trimmed from history searches.
`unscored` means the issue has no symptom predicate: #3150 is a specification gap with
nothing to reproduce, but its evidence still records two compiler-measurable claims.

`out-<compiler>--<predicate>.txt` is a probe of the same release under a *second* predicate
(`match-crash.json` and friends). The predicate is part of a probe's identity, so the two
histories are filed separately and the runner refuses to overwrite one with the other.

A `variant-*.txt` file is a control or a translated variant, never a probe of the primary
repro. Its `# expect:` header records what it must do — `no-match` for a known-good input the
predicate must not fire on, `match` for an identity control where sameness is the finding,
`invalid-probe` for one that is *meant* to be rejected before it reaches the code under test
— and `reindex` re-checks it on every run.

## Who may run what

`reindex` rebuilds the whole database: it deletes `issues` and `runs` and reconstructs them
from disk. That makes it **a collation-only command** — run it while per-issue sessions are
working and it will delete rows they are still writing. For the completeness check on its
own, use `triage.py audit [--issue N]`, which reads no tables and writes none.

Two commands revise recorded judgements without touching a measurement, and nothing else may:
`reindex --accept` restamps `# verdict:` headers that today's predicate code scores
differently, and `triage.py expect --issue N --capture F --expect V` revises a control's
declared expectation, refusing if the new declaration would itself be false. `# cmd:`,
`# exit:` and the captured output are observations; hand-editing them is falsification.

## Reproducibility check

The evidence is meant to stand without the session that produced it. Verify that rather than
assume it: give a fresh agent one issue directory, withhold `notes.md`, `verdict.json` and
`comment.md`, and ask it to derive the verdict and list what it could not determine.

Run it on any issue whose suggested action is `close-fixed`. Doing this on #3038 reproduced
the verdict and found that the control had been run by hand and never captured — a published
claim resting on nothing on disk. `triage.py run --shader X --label Y` exists so that
capturing a control is easier than not capturing it.

## Getting started on a new machine

```bash
cd .github/skills/dxc-issue-triage
python scripts/triage.py reindex          # rebuild the database from data/
python scripts/triage.py catalog --seed-from ../../../build/tools/clang/test/dxc_releases
python scripts/triage.py compiler --id main-debug --exe ../../../build/Debug/bin/dxc.exe \
                                  --commit $(git rev-parse HEAD)
```

`reindex` restores issues and runs. The release catalog and the local Debug build are
machine state, so they are re-registered rather than restored.

## reindex is a regression test, not just a restore

Run verdicts are re-derived by running today's predicate code over the archived output, so
`reindex` re-checks every historical probe and reports four kinds of problem:

- **probes today's code scores differently** — a predicate bug found while triaging one
  issue is retroactively applied to every issue already triaged;
- **probes captured with a command `cmd.txt` no longer specifies** — correcting a repro does
  not delete the outputs captured from the old one, and a superseded probe looks exactly as
  authoritative as a current one;
- **controls that no longer do what they were declared to do** — a variant captured with
  `--expect match|no-match` is an assertion, re-checked forever;
- **evidence a completed triage should have left behind** — a shader with no captured output,
  a missing `expected.md`, a verdict with no recorded reviewer.

All four have caught real problems: three #3873 probes left behind by a profile correction;
all 21 of #3768's probes still carrying a workaround removed from `cmd.txt`; and, on the
completeness audit's first run, **six of fifteen issues** with uncaptured control or variant
output — including two compiler-measured claims in #3150 that had been published with no
evidence on disk. None of them changed a verdict, and none was visible without the check.

This matters most because issues are triaged in **parallel, one session each**. A lesson
learned on one issue cannot reach the others while they are running, so collation re-scoring
everything is what applies it retroactively.

Know the edge: `reindex` cannot check reasoning. It will not tell you a repro is unfaithful to
the issue, that the predicate tests the wrong thing, or that a verdict misreads its own output.

A clean run prints `every probe re-scores as captured, none are stale, and no issue is missing
required evidence`. Treat anything else as a finding to explain before adding to the batch.

## Draft comments

`comment.md` files are drafts awaiting maintainer review. They open with a rendered warning
callout, because these files are browsable on github.com where an HTML comment is invisible
to exactly the audience that most needs to know a draft is a draft.

**This skill does not post anything.** Recommending an action and taking it are different
jobs; see the hard rules in `SKILL.md`.
