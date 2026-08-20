# Method notes — #5302

## Bisect's `invalid-probe` classifier does not catch an "absence of a mechanism" trap

`triage.py bisect --issue 5302 --linear` reported "always-repro'd across v1.4.1907..v1.9.2607"
with **no invalid probes flagged**. That is misleading: v1.4.1907 (2019-07) predates PR #2795
(2020-03-30, `d3af7f123`), which introduced `dx.break` in the first place. At that release,
`not_contains dx.break` is trivially satisfied for *both* `-T vs_6_0` and `-T ps_6_0` — the
mechanism does not exist yet for any shader stage, not just for VS specifically. The compile
succeeds cleanly (exit 0, valid DXIL), so none of the documented `invalid-probe` markers
(rejected profile, unknown identifier, internal failure, etc.) fire. This is the same
"absence-predicate satisfied for free" family of trap the skill already documents for a
*failed* compile, but here the compile *succeeds* and the absence is still vacuous, because
the feature the predicate is checking for is absent from the whole binary, not from one
predicate arm.

Resolution used here: a custom per-release matrix (`gen-release-history.py`,
`manual-case-release-history.txt`) that runs *both* `-T vs_6_0` and `-T ps_6_0` at every
stable release and reports `dx.break` presence for each. This surfaced the true boundary
(v1.5.2010 onward: PS has it, VS never does) and correctly flagged v1.4.1907 as invalid
evidence for this specific PS-vs-VS comparison, rather than folding it into "always
reproduced" the way linear bisect's plain summary did.

**Possible generalization for `SKILL.md`/`triage.py`:** the existing `invalid-probe`
documentation covers a release *rejecting* the repro. It does not yet cover a release whose
repro *compiles cleanly* but where the very feature the predicate's absence-clause is keyed on
did not exist yet at that release. A `--feature-control` mechanism analogous to the
already-documented "feature-presence control on every probed release" idea (see #8725/#2922)
would generalize this: for an absence predicate, run a *known-positive* sibling command per
release (here: the PS command) and treat a release where the sibling *also* lacks the
positive signal as invalid evidence for the primary predicate, without requiring a bespoke
manual matrix script each time. This is an issue-specific observation, not applied to shared
code from this per-issue session.

## CS control abandoned as unusable, not as a genuine negative

Attempted a compute-shader translation of the repro to broaden evidence beyond PS vs VS. The
repro's entry-point signature (`int main(int a : A) : SV_Target`-shaped, non-numthreads) isn't
valid for a CS entry point, so the attempt produced parse errors — a broken harness, not a
discriminating control. Deleted rather than kept, consistent with the skill's rule that a
control nobody can re-run, or one that measures a harness bug instead of compiler behaviour,
should not be published as evidence.

## Godbolt banner hazard reconfirmed

`godbolt-note.txt` had to avoid the literal string "dx.break" — CE's DXC panes always compile
with `-Zi -Qembed_debug`, which echoes the note's source into the panes via
`!dx.source.contents`, and asserting an absence with a note that names the very token would
manufacture a false "present" hit in the VS panes meant to show its absence. Worked around
with structural language (internal constant before `main`, phi-based loop accumulator)
instead of naming the token. This is a second instance of an already-documented hazard, not a
new class.
