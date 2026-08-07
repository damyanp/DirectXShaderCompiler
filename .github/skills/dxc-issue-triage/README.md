# DXC issue triage

Tooling and accumulated evidence for answering, per open DXC issue: **is there a usable
repro, does it still reproduce, and when did that change?**

`SKILL.md` is the procedure. This file describes what is stored here and how to pick it up.

## Layout

```
scripts/            triage.py, test_predicates.py, render_comments.py
data/issues/<nnnn>/ the evidence for one issue
data/reports/       one report per batch
.cache/             compilers and the database -- gitignored, regenerable
```

Everything under `data/` is committed. That is the point: a verdict nobody can re-check is
just an assertion, and these verdicts are the input to closing or keeping issues open.

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
`reindex` re-checks every historical probe and reports two kinds of disagreement:

- **probes today's code scores differently** — a predicate bug found while triaging one
  issue is retroactively applied to every issue already triaged;
- **probes captured with a command `cmd.txt` no longer specifies** — correcting a repro does
  not delete the outputs captured from the old one, and a superseded probe looks exactly as
  authoritative as a current one.

Both have already caught real problems: three #3873 probes left behind by a profile
correction, and all 21 of #3768's probes still carrying a workaround that had been removed
from `cmd.txt`. Neither changed a verdict, but neither was visible without this check.

A clean run prints `every probe re-scores as captured, and none are stale`. Treat anything
else as a finding to explain before adding to the batch.

## Draft comments

`comment.md` files are drafts awaiting maintainer review. They open with a rendered warning
callout, because these files are browsable on github.com where an HTML comment is invisible
to exactly the audience that most needs to know a draft is a draft.

**This skill does not post anything.** Recommending an action and taking it are different
jobs; see the hard rules in `SKILL.md`.
