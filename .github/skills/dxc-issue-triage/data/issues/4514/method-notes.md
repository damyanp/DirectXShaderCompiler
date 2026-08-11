# Method observations from triaging #4514

Recorded here rather than edited into `SKILL.md` / `triage.py`, per the
single-writer rule for a parallel batch. Collation decides what to promote.

## 1. Sweep a suspected-inert flag; do not reason about it

The `-HV` hazard cost four `run --args` invocations and about twenty seconds to
settle completely: `-HV 2016/2017/2018/2021` all reproduce, identically to no
flag at all. That is a stronger answer than any amount of argument about
whether the reporter's default mattered, and it produces four committed
captures that `reindex` re-checks forever.

Worth promoting as a standing move for any parse/lookup/language-semantics
issue: **before deciding whether a language-version flag belongs in `cmd.txt`,
run the sweep.** SKILL.md already says to verify that such a flag is
load-bearing (#3835's `-Wno-parentheses-equality`); what it does not say is
that the check is cheap enough to run unconditionally, and that the cheapest
form is a labelled `--args` variant per version with `--expect`, so the
negative result is on disk rather than in prose.

Note the asymmetry that makes this worth doing even when you never intended to
add the flag: the sweep also answers the *forward*-in-time trap (SKILL.md's
#2202 note — "pin the language version of any repro older than the current
default"). Here it showed that today's `-HV 2021` default does not change the
2022 shader's fate, so no pin was needed. One measurement, both directions.

## 2. Prove the `invalid-probe` suppression fired; do not assume it

This issue's symptom text contains `no member named`, which is literally one of
`classify()`'s feature-absence markers. SKILL.md's #3055 note says to write the
diagnostic verbatim into `match.json`, and that worked exactly as documented —
20 of 20 releases scored `repro` with no demotion.

But "it worked" was, at the time, an assumption. The cheap confirmation is:

```powershell
Select-String -Path *.txt -Pattern "invalid-probe" -SimpleMatch   # expect: nothing
```

Every demotion stamps `# invalid-probe-reason:` into the capture, so a zero
result is a positive statement that the suppression held. Suggest adding this
to the diagnostic-quality-issue guidance as a step, not just as an explanation
of why the predicate is written verbatim — an unverified suppression looks
identical to a suppression that never had to fire.

(Per SKILL.md's own warning, that scan must be `Select-String`, not the agent
`grep` tool, because this directory is under `.github/`.)

## 3. Pre-register predictions inside the control shader's comments

For the four mechanism probes here (`control-dummy-static`, `-dummy-struct`,
`-two-cbuffers`, `-reopen-after`), the predicted outcome was written as a
comment at the top of each shader *before* it was run, and the shader is
committed alongside the capture that answers it. That makes the prediction
falsifiable after the fact by anyone reading the directory, at zero extra cost,
and it extends `expected.md`'s "write it down before you run it" discipline
from the issue as a whole down to individual probes.

It is worth the effort specifically when a probe is testing a *hypothesis about
the mechanism* rather than the symptom: those are the probes where the
temptation to rationalise afterwards is strongest, because any result can be
narrated as consistent with some reading of the source. Two of the four here
were predicted to **fail**, which is what made the set discriminating.

Caveat found while doing it: SKILL.md warns that editing a captured repro's
comments desynchronises line numbers in captured diagnostics. The same applies
to these controls, so write the prediction before the first run and leave it
alone afterwards.

## 4. A control can turn out to be the finding

Pane 5 of the Compiler Explorer link (`hlsl_clang_trunk` with `-DUNQUALIFIED`)
existed only to satisfy SKILL.md's rule that a Clang result is not evidence
without a control. It then produced the single most interesting measurement in
the triage: Clang rejects the unqualified spelling that DXC accepts, and
accepts the qualified spelling that DXC rejects — the exact inverse. Without
the control pane, pane 4's bare exit 0 would have been reported, weakly and
correctly, as "Clang does not appear to have this bug", and the inversion
would have gone unnoticed.

The generalisable form: **for a lookup or name-resolution issue, the natural
control is the same shader with the other spelling**, and that control is
informative in both directions. Worth stating next to the existing
same-subject-near-miss guidance (#3066), which frames the near-miss purely as
a way to make a silence claim safe.

## 5. `godbolt --compilers` accepts the same compiler id twice

`"dxc_trunk:<args>,dxc_trunk:<args> -DWORKAROUND"` produces two distinct panes
and the shortener stores both correctly (verified through
`/api/shortlinkinfo`). `ce_compiler_specs` returns a list of tuples, so nothing
deduplicates by id.

This is the natural partner to SKILL.md's `-D<CONTROL>` guard device (#3872),
which is currently described only as "add a second pane" without saying that
the second pane may be the *same compiler*. For an A/B where the variable is a
source construct rather than a compiler, holding the compiler fixed across the
two panes is exactly what you want, and readers may not realise the spec
permits it.

## 6. `godbolt.txt` / `godbolt-source.txt` are not re-validated against `cmd.txt`

When `--source` is used, `ce_compiler_specs` correctly refuses to infer
arguments and demands an explicit `id:<args>` for every pane. Those arguments
are then persisted in `godbolt.txt` and reused verbatim on later runs.

The consequence is that the published CE arguments are pinned at the moment the
link was made and no longer track `cmd.txt`. `reindex`'s stale-probe check
compares captures against `cmd.txt`, and `godbolt.txt` is not a capture, so a
later correction to `cmd.txt` — the #3873 / #3768 scenario, which is exactly
what that check exists to catch — would leave a published link demonstrating
the superseded command with nothing reporting the divergence.

Not hit here (`cmd.txt` never changed), and the overrides were deliberate and
necessary, so this is a gap to consider rather than a defect that cost
anything. If it is worth closing, the check is cheap: warn when
`godbolt-source.txt` exists and `godbolt.txt`'s overrides no longer contain the
flags `cmd.txt` specifies.

## 7. Minor: `compilers` table column names

`triage.py sql "SELECT exe, commit_sha FROM compilers"` fails; the columns are
`exe_path` and `git_commit`. One wasted round trip. Not worth a code change,
but `SELECT sql FROM sqlite_master WHERE name='<table>'` is the quick way out
and could be mentioned under "Useful queries".
