# #3429 — method observations

For collation to promote or discard. Nothing here was written to `SKILL.md` or `scripts/`.

## 1. A diagnostic's *framing* changes across releases even when its rule text does not — and
that fakes a transition

**This is the finding of this issue, and it produced a wrong history before it was caught.**

SKILL.md already says message text is not portable across platforms, and not portable across
release ages ("#3259's v1.5.2010 access-violates with completely empty stderr"). Both of those
warnings are written about *crash* predicates, and both are answered by the same advice: use
the exit status. **That advice is unavailable when the reported symptom IS the diagnostic** —
every release exits 0x80004005, so the exit code cannot discriminate at all, and a text
predicate is the only option available.

What happened: `match.json` began as
`contains "error: TGSM pointers must originate from an unambiguous TGSM global variable."`,
lifted verbatim from the reporter's 2024 paste — which felt like the *most* rigorous choice,
since SKILL.md's #3055 rule explicitly says to "write the diagnostic text into `match.json`
rather than approximating it". `bisect --linear` then reported:

```
result: non-monotonic history, transitions at v1.5.2010 -> repro
```

v1.4.1907 in fact fails identically. It just words it differently:

```
at 0x2221ed5c658 inside block .lr.ph._crit_edge of function main TGSM pointers must originate from an unambiguous TGSM global variable.
```

No `error: ` prefix, an instruction address and block name instead of a source line:column and
the IR text. Only the *framing* around the rule changed, at some point after 2019; the rule
string itself is stable, because it comes from `hctdb.py`'s `add_valrule` table and is
generated into the validator.

The result read entirely plausibly — a 2021 issue "regressing" at the last release before it
was filed is a *better* story than "always broken", and `--linear` had dutifully printed 20
rows to support it. Nothing warned. It was caught only by opening `out-v1.4.1907.txt` to ask
why the oldest release differed.

Two things worth promoting:

- **For a diagnostic-symptom issue, quote the smallest stable part of the message**, which for
  a DXIL validation rule is the `hctdb.py` rule string with no `error:`/`warning:` prefix and
  no surrounding framing. The prefixes are driver formatting and have changed at least once.
- **`bisect` reporting a transition at the second-oldest release deserves a manual look at the
  oldest capture before it is believed.** That shape — one dissenting endpoint — is what both
  the `invalid-probe` trap and this trap look like from the outside. A cheap tool-side check
  would be: when a linear scan's only disagreement is a single endpoint, print that capture's
  output alongside the summary rather than just its verdict.

The falsifying capture is preserved as `manual-case-predicate-correction.txt`.

## 2. `godbolt-note.txt` is already `//`-commented by the tool; do not comment it yourself

`annotate()` (triage.py:1556-1559) wraps the note in a `//` rule and prefixes **every line**
with `// `. A note written as HLSL comments therefore publishes as `// // …` on every line.
Cosmetic only, and it cost one extra publish + verify cycle to notice. SKILL.md describes the
file as a "`// What to look for` banner", which reads as though the `//` is the author's job.
Suggest rewording that to "a *what to look for* banner (the tool adds the `//`)".

## 3. A `-Vd` pane is a cheap way to make a validation-failure link *show* something

SKILL.md: "A link that makes the bug visible beats one that merely reproduces it." For an
issue whose entire visible behaviour is an error message, the natural conclusion is
`--skip "one-line error, nothing to see"`. But `--compilers "…,dxc_trunk:<args> -Vd"` puts the
*rejected module* on screen next to the rejection, which is the actual evidence. Worth adding
to step 7 as the standard move for validation-failure issues, beside the existing FXC and
Clang comparison examples.

## 4. The documented PowerShell backtick/`$` trap, hit again

Writing a here-string containing `` `error: `` through `$py | python -` is safe, but writing
the same text through a `@"..."` (double-quoted) PowerShell here-string is not: `` `e ``
became `U+001B`, so a file written that way came out reading `rror:`. SKILL.md documents this
exactly; it is still easy to walk into when the prose being written is *about* compiler
output, which is precisely when it contains backticks. It was caught here only because the
mangling was visible in the echoed output. Prefer writing prose files with an editor, or via
a **single-quoted** here-string piped to Python — the latter is what this directory's
generator scripts do.

## 5. Related issues (for collation to judge, deliberately absent from the draft)

Per SKILL.md, cross-issue claims belong to collation, so `comment.md` makes no
"duplicate of" claim. Recorded here:

- **#2768** (2020-03, closed 2020-09 for lack of reporter response) — same rule, groupshared
  array in a compute shader, and its quoted output uses the *old* `at 0x… inside block …`
  format, which independently corroborates finding 1. It was closed on the assumption that a
  maintainer's suggestion had resolved it, not on a verified fix.
- **#4436** (closed 2024-04 as completed) — same rule text, but an amplification-shader
  payload reached through a chained GEP. That family was genuinely fixed; `git log` on the
  check shows `74480d1e7` ("Allow inner constant GEP for GEP and BitCast instructions") and
  `cd71b1795` (#8575, "Drill through chained GEPs for TGSM"). Neither touches the `phi` case,
  which is why #3429 survived work that closed its look-alike. Something for collation to
  weigh: an issue can look fixed-by-association when only one of the rule's failure modes was
  addressed.

## 6. Small note on `audit`

`audit --issue 3429` was run before reporting, per the brief. It printed exactly:

```
#3429: pending collation -- no reviewed_by yet (step 10 is a batch step; do not fill it in yourself)
no missing evidence in 1 issue(s)
```

Two things worth passing on. First, it scoped itself to the one issue and reported nothing
about peers, which is what you want during a parallel phase — batch 008's brief banned it and
one worker ran it anyway; that worker was right, and this is a second independent data point
that the per-issue completeness check is worth keeping available. Second, the `reviewed_by`
line is phrased as a reminder rather than a defect, which is the correct shape: it would
otherwise read as a finding the worker is expected to fix, and fixing it means filling in a
batch-level field yourself. I did not verify anything about what `audit` does to the database
beyond the fact that it produced no errors and the run completed; the read-only claim here is
the brief's, not my own measurement.

## 7. `grep` returns a silent false zero under `.github/` unless a `glob` filter is passed

Measured in `manual-case-grep-hidden-path.txt`. Two wrong diagnoses preceded the right one, so
the sequence is worth recording as well as the result.

I first recorded this as "`grep` false-negatives when `paths` is a single file". Wrong — I had
one directory query that worked and concluded the path shape was the variable. The orchestrator
then measured `grep` finding **zero** files containing `dxc-issue-triage` under `.github/` where
`Select-String` finds 15, and concluded `grep` is unusable under `.github/` at all — `.github`
is hidden and ripgrep skips hidden paths by default. That is the right cause but slightly too
strong as a rule. Controlled probes give a sharper line:

| query | result | truth |
| --- | --- | --- |
| `TGSM`, dir, **no glob** | `No matches found` | 61 files |
| `audit`, dir, **no glob** | `No matches found` | 1 file |
| `audit`, single file, **no glob** | `No matches found` | 1 file |
| `TGSM`, dir, **glob `*.txt`** | 105 matches / 49 files | 49 `.txt` files ✓ |
| `audit`, dir, **glob `*.md`** | 1 file ✓ | 1 file ✓ |

So the trigger is the **absence of a `glob`**, not the path shape: 4 of 4 glob-less queries
returned false zeros, 3 of 3 glob'd queries were accurate. The one query of mine that worked was
the one that happened to carry `glob: *.md`, which is what misled me into blaming the file path.

Why this matters more than an ordinary tool bug: the failure mode is a clean `No matches found`
with no error, so it is **indistinguishable from a true negative** — and the check it corrupts is
"does my write-up still assert the thing I just removed?", where the worker *wants* to see zero.
It confirms whatever you were hoping to confirm. §6 above is a worked example: a glob-less grep
for `audit` over `method-notes.md` returned nothing while the word sat on lines 101 and 103.

Rule adopted: whenever a **zero** result is the meaningful answer, verify with `Select-String`,
which has no hidden-path behaviour. Use `grep` under `.github/` only with a `glob`. The separate
`glob` tool is unaffected.
