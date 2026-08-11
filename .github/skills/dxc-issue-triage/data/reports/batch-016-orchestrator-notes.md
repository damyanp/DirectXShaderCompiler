# Batch 016 — orchestrator notes

Channel from the orchestrator to the batch-016 collation session, which by design never sees
the orchestration conversation. Everything here is something the collation cannot learn from
the issue artifacts alone.

Batch: **4514, 4520, 4527, 4540, 4549, 4605, 4614, 4615, 4619, 4629** — the next ten of the
oldest 100. This batch takes the pass to 91/100; a final batch of nine follows.

Ground truth: `main-debug`, version `1.9.0.5433`, public commit `13730886e`.

---

## 1. `reviewed_by` produced a false alarm across the whole of batch 014, and the cause was a briefing gap

Batch 014's independent draft review genuinely happened: a different model reviewed all ten
drafts, produced per-issue edits and two factual corrections, and both corrections were
verified and applied. But `reviewed_by` was never stamped on any of the ten verdicts, so the
next rebuild reported **all ten as unreviewed** — the exact signal the field exists to raise
when a review has been *skipped*.

The cause was a boundary instruction working as designed and colliding with a deliverable. The
collation session was told to write only the report and not to touch any issue directory,
precisely so it could not quietly rewrite a worker's evidence. `verdict.json` lives in the
issue directory. So the instruction that protects the evidence also blocked the one field
collation is supposed to own.

The fix is in the briefing, not the tooling: **collation must be told explicitly to stamp
`reviewed_by`**, as an exception to the otherwise-total boundary. Batch 015's collation brief
carries that instruction; batch 016's must too.

The general lesson is worth more than the specific fix. A mechanical completeness check is
only as good as its ability to distinguish "did not happen" from "happened but left no
trace". This one could not, and it cost a rebuild cycle to work out which it was. When a
check fires, the first question is which of those two it is — and if the artifacts cannot
answer that, the check needs a stronger witness, not a louder warning.

## 2. `--expect` conflation is fixed, and the one affected capture now reads correctly

`--expect` treated every declared expectation as a **control assertion** — a claim about an
input already known to be good. It was also being used, reasonably, for **hypothesis probes**,
where the point is to find out. When such a probe was refuted, that refutation was a genuine
finding, but it was recorded identically to a control that had rotted, and re-reported as a
defect on every single rebuild.

`triage.py` now has `--hypothesis`, which records the same expectation as a prediction whose
supported/refuted outcome is itself evidence. The one affected capture — the
`-validator-version 1.4` probe on #4206 — has been re-recorded. Its captured output is
byte-identical; only the header changed, from a failed control to
`# expectation-kind: hypothesis` / `# outcome: refuted`. The rebuild is now clean.

Worth noting *how* that defect was found: the worker recorded a prediction on a probe whose
answer it did not already know, and wrote down that the prediction was refuted rather than
quietly presenting a mechanism it had not checked. The tooling gap only became visible because
someone used the flag honestly.

## 3. Captured output is now redacted at the generator, and the allowlist was the wrong instrument

A Debug build bakes absolute `__FILE__` paths into its own diagnostic output, so a genuine,
unfalsified capture can contain this machine's checkout layout. One worker found this, and
initially hand-edited the five affected captures — then caught itself, reverted, correctly
identified the edit as falsification of evidence, and asked for a decision instead.

Two candidate remedies. The **allowlist** was rejected: every existing entry is either prose
*about* paths or a path already public in the issue itself, whereas this was a private
detail of one machine, published nowhere. The gate exists to prevent exactly that.

The fix went into the **generator**. `redact_paths()` tokenises the checkout, triage and cache
roots, matching either separator, repeated separators and any case, and is applied to stdout
and stderr in `_run_command_list` **before the capture is written and before it is scored** —
so the predicate sees exactly what a reader sees, and the two can never disagree.

The precondition that made this safe was checked first, not assumed: **no predicate anywhere
keys on a machine path**, verified across all 127 matchers. Re-verify that if predicates
change. All 54 affected captures were regenerated and re-scored identically.

The worker's own error is the instructive part. It concluded the generator *could not* be
fixed, reasoning that a predicate scores the body, so the body must stay verbatim. The first
half is true; the conclusion does not follow. It only means the tokenised text must be what
the predicate sees — which is a statement about ordering, not about impossibility.

## 4. Pipelining is safe under a narrower rule than "never change tooling"

Batches are now pipelined: batch N+1 is dispatched while batch N is being collated. That means
tooling can change while workers are live, which earlier notes treated as forbidden.

Measurement suggests the real rule is narrower: **changes made under live workers must be
additive and monotonic in strictness.** Both changes above qualify. `--hypothesis` and
`quote_from` are opt-in, so a worker that does not use them sees prior behaviour exactly. The
path gate and `redact_paths()` only ever became stricter, never looser. A change that *relaxed*
a check, or that altered scoring for existing flags, would not qualify and must wait.

## 5. Provenance: `triaged_by` is self-reported and unreliable

Twenty-two distinct spellings now exist across the pass, and the field is not merely
inconsistent — it is **wrong**. Three batch-015 workers, all dispatched on `claude-opus-5`,
self-reported `claude-opus-4.5`, `claude-opus-4.5` and `GitHub Copilot CLI (Claude Sonnet
4.6)` respectively. Models do not reliably know what they are.

The orchestrator knows which model it dispatched; that is the only ground truth available.
The field should be orchestrator-set or auto-stamped rather than self-reported. Not changed
mid-pass, because rewriting it retroactively would flatten genuine cross-batch model
differences that the record may later need. Treat any existing `triaged_by` value as a hint,
never as provenance.

## 6. Visibility audit baseline moved 28 → 29, and the new event is not ours

The audit found one new visible event: a cross-reference on issue 8517 by actor `Copilot`,
timed during this session. Traced to PR 8749, *"Fix crash when heap subscript result is
discarded"* — an unrelated Copilot coding-agent change in the upstream repository. Neither
8517 nor 8749 is in the triage set, and every triage commit remains local and unpushed, so a
local commit cannot have produced a timeline event.

Recorded because the conclusion, not just the number, is what a future audit needs: **the
baseline is 29, and the 29th event has an identified external cause.** An unexplained
increment is the thing to escalate on.

## 7. `overview.md` is generated, and regenerating it at the wrong moment corrupts a commit

`scripts/render_overview.py` takes no arguments and always rolls up **everything currently on
disk**. Run while a batch is in flight, it produces a rollup referencing issue directories that
are not yet committed, and the committed tree then contains dangling links.

The snapshot committed with batch 015 was deliberately generated *before* batch 016 was
dispatched. Regenerate only when no batch is in flight, and check the printed issue count
matches what is actually being committed.

Batch 014's collation did not update `overview.md` at all, which is how this was noticed —
the rollup silently stopped at batch 013 while the per-batch reports carried on.

## 8. There are two release cache roots, and scanning one of them under-counts history

This one has now caused a real error in published evidence.

Releases live in **two** places:

- `.github\skills\dxc-issue-triage\.cache\compilers\releases\` — the lazily-downloaded cache
- `build\tools\clang\test\dxc_releases\` — the tree adopted from DXC's own test
  infrastructure via `catalog --seed-from`

Neither is a superset of the other. `v1.8.2502` and `v1.8.2505.1` exist **only** in the seeded
root; `v1.5.2003`, `v1.7.2207` and many others exist only in the cache.

Issue 4256 (batch 014, already committed) concluded that `dxv.exe` "first appears in a stable
release archive at v1.8.2505" and that **four** releases ship it. Checked across both roots,
`dxv.exe` ships in **six** releases and the true floor is **v1.8.2502**. A batch-015 worker hit
the same trap on the same instrument, noticed that four releases had come back "not-cached",
and corrected itself — which is the only reason the discrepancy was visible at all.

Two things make this worth promoting rather than just fixing:

- **The error understated the evidence.** The corrected finding is stronger: the behaviour
  holds over six releases back to v1.8.2502. An error in this direction is far harder to catch
  by reading, because nothing looks wrong — the story is merely smaller than the truth.
- **It was caught by cross-checking two issues against each other**, not by re-reading either.
  Two workers measured the same instrument independently and disagreed about how many releases
  ship it. That disagreement is a cheap, mechanical signal, and it is available whenever two
  issues touch the same tool. Worth looking for deliberately at collation.

Any claim of the form "the first release that ships X" or "the N releases that have X" must be
computed over **both** roots. A per-release "not-cached" count in a harness's own output is the
cheap witness that the scan was complete; treat a non-zero one as an unfinished measurement
rather than as a fact about the release.

## 9. `classify` only protects one direction, so a diagnostic-shaped symptom can fake a repro

`invalid-probe` detection is the safety net against a release that never reached the code under
test — it predates the profile, or lacks the feature, so it rejects the input and scores clean.
The runner catches that and `bisect` trims those probes off the ends of the range.

**But `classify` only ever demotes a `no-repro`.** It cannot demote a `repro`. That asymmetry is
invisible until the symptom *is* a diagnostic, and then it inverts the whole protection:

Issue 4605's symptom is the error `Explicit template arguments on intrinsic Load are not
supported`. A release predating templated `Load<T>` emits **the same message** for its own
reasons. Such a release therefore scores `repro`, not `no-repro` — so the safety net never
fires, and a feature that did not yet exist is recorded as a defect that already reproduced.
The failure is silent in both the tooling and the report.

The only instrument that can detect this is a **per-release control that proves the feature was
present**. 4605 used an untemplated `RWByteAddressBuffer` variant compiled on every release; it
succeeds on all 20, which establishes the feature existed throughout and that the shared
diagnostic is not a feature-absence artifact. Ancestry corroborated it independently.

So: **whenever the symptom is a diagnostic rather than a crash or a wrong value, a per-release
positive control is not optional.** Without one, "always repro'd" is unfalsifiable — it is
exactly what a never-implemented feature also looks like. Note that this is the *opposite*
error from the one the invalid-probe machinery was built for, which is why the machinery does
not catch it.

A related observation from the same issue: **5 of 20 releases carry no usable build identity.**
v1.4.1907–v1.6.2106 reject `--version`, and v1.5.2010–v1.7.2207 report only a generic
`clang version 3.7`. Those releases are attributed by cache path alone, which is worth stating
wherever a per-release matrix claims to identify what it ran.

## 10. The registered ground-truth commit and the binary's self-reported commit disagree, and the disagreement is only benign by accident

The `compilers` registry records `main-debug` at git commit `13730886e` ("Improve Copilot
release note review guidance"), which is an **upstream main** commit. The binary itself reports
`1.9.0.5433 (triage, ab5400907)` — a *different* commit, the merge of `upstream/main` into the
`triage` branch. Batch-016 verdicts cite `13730886e` via `--triaged-with-commit`.

This was checked rather than assumed. `13730886e` is an ancestor of `ab5400907`, and
`git diff 13730886e..ab5400907 --name-only` yields **597 files, every one of them under
`.github/skills/dxc-issue-triage/`**. So the compiler source at the build commit is identical to
upstream main at `13730886e`, and attributing verdicts to the upstream commit is not merely
defensible, it is the more useful attribution: it names the commit a reader can check out.

**The hazard is that this holds only as long as the triage branch touches no compiler source.**
Nothing enforces that. The moment a source change lands on `triage`, the registry keeps
reporting an upstream commit that the binary was not built from, every verdict silently
inherits the wrong attribution, and the two numbers still look exactly as consistent as they do
today. The check that separates the safe case from the unsafe one is the name-only diff above,
and it needs re-running whenever the ground truth is rebuilt — not once.

A weaker version of this already bit batch 004, where the same diff was run against `eff900d54`
and reported "0 files outside the skill directory". That it passed then is why it was not
re-run since; passing once is not a property of the setup, only of that moment.

Note also that three sibling registrations disagree among themselves: `main-debug-pix` and
`main-debug-refl` record `ab5400907` while `main-debug` and `main-debug-fc` record
`13730886e`. Both are correct descriptions of the same build, which is precisely why the
inconsistency is invisible in any single issue's provenance line.
