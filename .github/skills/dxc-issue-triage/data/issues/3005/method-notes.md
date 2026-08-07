# Method notes — #3005

Observations about the triage method and tooling, recorded for collation. Not
fixed here; nothing outside `data/issues/3005/` was touched.

---

## 1. No predicate kind can see a file dxc writes (headline)

**This is the second independent confirmation that the gap is systemic.** The
brief says a previous issue in the last batch hit the same wall and had to
measure its evidence by hand into a `manual-case-*.txt`, leaving the
decision-relevant fact invisible to `audit` and to the reports. #3005 hit it
too, and hit it harder: for #3005 the file *is* the entire symptom. There is no
text at all.

### The shape of the gap, precisely

`_eval_match` (`scripts/triage.py:453`) takes exactly `(m, text, rc, timed_out,
path)`. Every leaf kind is a function of those three values:

| kind | reads |
| --- | --- |
| `contains`, `not_contains`, `regex`, `not_regex` | `text` |
| `internal_failure` | `text`, `rc`, `timed_out` |
| `nonzero_exit` | `rc`, `timed_out` |
| `timeout` | `timed_out` |
| `any_of`, `all_of` | their children |

`text` is built in `cmd_run` (`scripts/triage.py:1036-1052`) by concatenating
per-invocation stdout/stderr chunks. Nothing else ever enters it. **The
filesystem the compiler just wrote to is not an input to the predicate system,
at any level.**

For #3005 the symptom is a `uint32` at offset `0x28` of a `.pdb`. The
strongest possible demonstration of the gap is committed as
`variant-compile-only-main-debug.txt`: the exact compile that produces the
defective file, **exit 0, empty stdout, empty stderr**. There is no text
predicate — none, in any combination — that could distinguish a good build from
a bad one there.

### What it costs

1. `match.json` has to be about something *other* than the symptom (see §3).
2. The real evidence lives in `manual-case-msf-header-history.txt`, which
   `audit` cannot re-derive and `render_overview.py` cannot summarise. If the
   bug were fixed tomorrow, `reindex` would happily re-run the predicate, get
   `repro`, and report the issue as still broken. **The self-checking property
   that the whole harness is built for does not extend to this issue.** That is
   the actual harm, and it is silent.
3. A reader of `overview.md` sees `repros` with no way to know that the
   `repro` came from a precondition, not the symptom.

### Concrete proposal: a `script` predicate kind

Minimal, general, and it composes with everything that already exists. Add one
step in `cmd_run`, between the invocation loop and `text = "\n".join(chunks)`:
if `match.json` (or a sibling `probe.txt`) names a checker, run it in the issue
directory *after* the dxc commands and append its stdout to `text` as one more
chunk, e.g.

```
$ probe measure_msf.py --file pdb/repro.pdb
[exit] 0
--- stdout ---
NumBlocks       : 10
BLOCKS ON DISK  : 11
SYMPTOM         : PRESENT
```

Then existing text predicates work unchanged:

```json
{"kind": "all_of", "value": [
  {"kind": "contains", "value": "; shader debug name: pdb/repro.pdb"},
  {"kind": "contains", "value": "SYMPTOM         : PRESENT"}
]}
```

Why this design rather than a bespoke `file_bytes` / `artifact` kind:

- **It reuses the whole existing predicate vocabulary.** No new matching
  semantics, no new `invert` interactions, no changes to
  `_has_positive_clause` or `_is_absence_predicate`.
- **The evidence stays in the captured text**, so `run`, `bisect`, `audit`,
  `reindex` and the probe files all keep working with no further change, and
  the measurement appears verbatim in `out-*.txt` where a human reviewer reads
  it. A `file_bytes` kind that returned a bare boolean would leave the
  captured file just as silent as it is today.
- **It generalises past this issue.** Any artifact symptom — PDB bytes, `-Fo`
  container layout, reflection blob contents, `-Fre` output, file size, file
  *absence* — becomes expressible by writing a checker, which issues already
  do anyway (this workspace has an established `measure.py` + `manual-case-*`
  pattern; that pattern is exactly this feature, done by hand and disconnected
  from the harness).
- **It keeps the checker reviewable.** The script is committed next to the
  repro and is re-runnable from a clone, which is the existing standard of
  evidence.

Requirements it would need to meet, learned here:
- run with `cwd` = the issue directory, like the dxc invocations, so paths in
  `cmd.txt` and the checker agree;
- run *after all* `cmd.txt` lines, since the artifact may be written by line 1
  and read by line 2;
- have its exit code kept **out** of `worst_rc` — a checker reporting "symptom
  present" must not look like a compiler failure to `nonzero_exit` or to the
  `invalid-probe` guard;
- be skipped, with the reason recorded in the captured text, when the compile
  failed — otherwise a checker reading a *stale* artifact from a previous run
  produces a false `repro`. This is not hypothetical: it is exactly why the
  broken-shader control was rejected for this issue (`notes.md` §5).

### Second-order note

The `--repeat`, `--shader` and `--args` machinery all assume the interesting
output is textual. If a `script` kind lands, `--shader` controls become usable
for artifact issues too — but only if stale artifacts are cleaned between
runs. Today `pdb/repro.pdb` survives from run to run, which is a live trap for
anyone writing an artifact control by hand.

---

## 2. `cmd.txt` is split with POSIX `shlex`, which silently deletes backslashes

`scripts/triage.py:1039` — `subprocess.run([exe] + shlex.split(line), ...)`.
`shlex.split` defaults to POSIX mode, where a backslash is an escape
character. On Windows, where every natural path uses backslashes:

```
>>> shlex.split(r'-Fd pdb\repro.pdb -Fo pdb\a.dxbc')
['-Fd', 'pdbrepro.pdb', '-Fo', 'pdba.dxbc']
```

Verified directly. There is **no warning**; dxc is simply handed a different
path than `cmd.txt` reads as saying, and it succeeds, writing to the wrong
place. Every artifact-producing repro on Windows is exposed to this, and so is
anything using `-I`, `-Fh`, `-Fe`, `-Fre`, or an `#include` path.

Worked around here by using forward slashes (dxc accepts them on Windows).
`ce_args` (`scripts/triage.py:1444`) uses the same `shlex.split`, so a CE link
built from a backslash `cmd.txt` would be silently wrong in the same way.

Cheapest fix: `shlex.split(line, posix=False)` on Windows, or strip the
resulting quotes; either way the current behaviour deserves at minimum a
warning when a token contains a backslash.

---

## 3. A "precondition predicate" as a feature-presence control — usable, but it
changes what `# verdict: repro` means

Since no predicate could express #3005's symptom, `match.json` was written to
assert something true and useful instead: that a separate PDB was *requested,
written, and read back*. Both clauses are positive, so the absence-predicate
guard is satisfied honestly and the runner's absence-only warning correctly did
not fire.

This works, and it is better than a predicate that pretends. But it has two
sharp edges worth recording as a general pattern, not just as this issue's
quirk:

1. **`# verdict: repro` in every `out-*.txt` now means "the precondition
   held", not "the bug is present".** Anyone reading those files, or
   `overview.md`, or `verdict.json` without also reading `match.json`'s `note`
   will misread them. Mitigated here by opening the `note` with *"READ THIS
   BEFORE TRUSTING A `repro` VERDICT ON THIS ISSUE"*, but a `note` is prose in
   a file nobody is required to open. A machine-readable marker — say
   `"asserts": "precondition"` — that `render_overview.py` could render as a
   flag would fix this properly.

2. **`bisect` output becomes actively misleading.** `bisect --linear` reported
   `v1.4.1907 no-repro` and "non-monotonic history, transitions at v1.5.2010".
   Read naively that says the bug was introduced in v1.5.2010. It says nothing
   of the sort: v1.4.1907 exhibits the defect identically, but its
   `dxc -dumpbin` cannot read a PDB (`error: Invalid bitcode signature`,
   exit 1), so the precondition fails. The bisect is measuring the age of a
   *dxc feature*, not the age of the bug. Nothing in the tool's output could
   possibly signal this; it is recorded prominently in `notes.md` §4 instead.

---

## 4. `godbolt` links only the first line of a multi-invocation `cmd.txt`

`ce_args` prints `warning: multi-invocation cmd.txt; linking the first only`
and drops the rest. Correct and clearly documented, but it means a two-stage
repro (write artifact, then read it back) is structurally unrepresentable on
CE — the second stage is where all the interesting output is.

Separately, and more generally useful: **CE's sandbox has no subdirectories.**
The local `cmd.txt` writes to `pdb/`, and CE returned
`No such file or directory pdb/a.dxbc` — plus, on `dxc_1_6_2112`, `exit=139`
(SIGSEGV) rather than a clean diagnostic. Both are artefacts of the sandbox,
not of the issue, and publishing that link unexamined would have been a wrong
result presented as evidence. Worked around with a per-compiler `id:<args>`
override writing to CE's own cwd, recorded in `godbolt.txt`, and the departure
is spelled out in `godbolt-note.txt` so the published pane explains itself.

That `-Fo` into a nonexistent directory makes dxc 1.6.2112 crash rather than
diagnose might be worth an issue of its own; it is out of scope here and is
*not* mentioned in `comment.md`.

---

## 5. Smaller things

- **`cmd.txt` comments must start at column 0.** The filter is
  `not ln.startswith("#")` (`scripts/triage.py:1019`), applied to the raw
  line, while the same expression `.strip()`s for emptiness. An indented `#`
  comment is passed to dxc as arguments.
- **git cannot store an empty directory, and dxc will not create the `-Fd`
  parent.** A repro that writes artifacts therefore needs a committed
  placeholder; `pdb/.gitignore` containing `*` and `!.gitignore` does the job
  and keeps the outputs untracked. Worth being a documented convention if
  artifact repros become common.
- **`--args` replaces the entire command** and needs `--label`, or it clobbers
  the primary capture (the tool does warn). `--shader` only swaps the `.hlsl`
  operand, which is the safer control mechanism — but see §1's note about
  stale artifacts before using it on an artifact issue.
- **`gh pr view --json merged` is rejected**; the field is `mergedAt`. Minor,
  but it cost a round trip while establishing the fate of PR #5767, which
  turned out to be the most important finding on this issue.
- **`--triaged-by` cannot be filled in honestly by the agent.** Nothing in the
  environment identifies the model — `COPILOT_CLI_BINARY_VERSION` is available,
  a model id is not — so an agent asked to record who triaged the issue must
  either guess or hedge. Existing rows are all specific model names, which
  means some of them were guessed. If the field is meant to carry weight (and
  SKILL.md says verdicts are weighed by which model produced them), the
  harness should supply it rather than asking the agent to introspect.

---

## 6. Cross-issue observation (kept out of `comment.md` per the brief)

The closure of PR #5767 on 2026-01-22 — *"This PR was closed as it has not been
updated in the last two years"* — is the **same inactivity sweep** SKILL.md
already records as having closed the `Fixes #2427` PR. That is now two triaged
issues whose only blocker is a swept, review-complete pull request. If the
pattern recurs across the batch it is a finding about the repository's process
rather than about any one issue, and collation is the place to say so. Checking
`gh api .../issues/<N>/timeline` for lapsed resolutions looks like it should be
a standard step in the per-issue workflow rather than a hazard note — for
#3005 it changed the suggested action.
