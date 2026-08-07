# #3055 — method notes

Observations about the *method*, for collation to promote or discard. Nothing here was fixed
in `SKILL.md` or `scripts/triage.py` by this session; both are untouched.

---

## 1. `invalid-probe` vs. a diagnostic-shaped symptom — measured, and it is real

**Result: it did not affect #3055 (negative), but the mechanism is confirmed and it fires in
both directions on inputs that are one word away from #3055's own.**

### The concern

`classify()` (`scripts/triage.py:637`) demotes a probe to `invalid-probe` when the output
matches an `unsupported` regex, on the theory that the compiler "rejected the input without
ever reaching the code under test". That test is a **diagnostic-text match**. When the
reported symptom is itself a diagnostic, the classifier's signal and the symptom are the same
kind of observation, so it can discard exactly the probes that matter.

The `unsupported` list (`triage.py:681-687`) is:

```
invalid profile | unsupported profile | unrecognized (argument|option) | unknown argument |
is not supported | requires shader model | CodeGen not available | recompile with -D |
use of undeclared identifier | unknown type name | no member named |
no matching function for call to | for non-scalar types use 'select'
```

The last five are ordinary front-end diagnostics. They are there for good reasons (#3038's
`use of undeclared identifier 'RayQuery'`, #2202's `select`), but they are not reserved words:
a compiler emits them for present-day mistakes just as readily as for absent features.

### What was measured

Three real dxc runs against the ground-truth build, re-derived in
`manual-case-classifier-branches.txt`:

| capture | predicate alone | marker in output | classifier says |
| --- | --- | --- | --- |
| `out-main-debug.txt` (#3055's repro) | repro | — | `repro` ✓ |
| `variant-methodology-freefn-main-debug--match-methodology-freefn.txt` | no-repro | `no matching function for call to` | **`invalid-probe`** ✗ |
| `variant-methodology-arity-main-debug--match-methodology-arity.txt` | repro | `use of undeclared identifier` | **`invalid-probe`** ✗ |

Both failure directions occur, and both are on real dxc output, not synthesised text.

**Direction A — `triage.py:688`, `verdict == "no-repro" and unsupported`.** Shader
`probe-freefn-good-diagnostic.hlsl` passes a `SamplerComparisonState` to the intrinsic
*function* `clamp`. dxc compiles it, runs overload resolution, and answers **completely and
correctly**:

```
error: no matching function for call to 'clamp'
note: candidate function not viable: no known conversion from 'SamplerComparisonState' to 'vector<float, 1>' for 2nd argument
```

That is a good diagnostic. For a diagnostic-quality issue, a good diagnostic is **what a fix
looks like** — so the correct score is `no-repro`, meaning "fixed here". The runner instead
records `invalid-probe`: *this compiler never ran the repro, evidence of nothing.* `bisect`
trims those off the ends of the range and never sees the transition. **On a diagnostic issue,
this direction can hide the very release that fixed it.**

**Direction B — `triage.py:713`, the absence-predicate branch.**
`probe-arity-undeclared.hlsl` calls `clamp` with four arguments. No overload takes four, and
dxc answers `error: use of undeclared identifier 'clamp'` — wrong and useless, since `clamp`
is plainly declared; a perfectly fileable diagnostic bug of exactly #3055's class. A triager
predicating on that message gets a predicate that **matches** (the symptom is present), and
`_is_absence_predicate` is true, and the symptom text *is* a marker — so the probe is
discarded. Every release would be discarded, including the ground truth, and `cmd_bisect`
then exits `no release could run this repro; retarget it at a profile/flag set the releases
support`, which misattributes the cause to the repro's profile.

Note the branch is reachable from a **mixed** predicate, not just a pure absence one:
`_is_absence_predicate` (`triage.py:684`) returns true if *any* sub-predicate of an `all_of`
is absence-based. #3055's own `match.json` is such a mixed predicate.

### Why #3055 escaped

Purely because of the word "member". dxc says `no matching **member** function for call to`
for an intrinsic *method*; the marker is `no matching function for call to`, which that string
does not contain. Delete one word — which is exactly what dxc prints for an intrinsic
*function*, measured above — and #3055's ground-truth probe becomes `invalid-probe` under its
own predicate, and the linear scan reports nothing at all.

So the negative result for #3055 is genuine but it is a one-word margin, and #3055 is not a
special case: it is a `diagnostic`-labelled issue whose predicate quotes an error message,
which is what every issue in that label looks like.

### Suggested direction (for collation to decide, not done here)

The classifier is inferring "the compiler never reached the code under test" from evidence
that does not support it. Some options, in rough order of how well they target the actual
inference:

1. **Make the marker test conditional on the predicate not being about diagnostics.** If any
   `contains`/`regex` clause of the issue's own predicate is a substring of — or overlaps —
   the matched marker, the marker is measuring the symptom, not feature absence, and should be
   ignored. That is exact for both directions measured here.
2. **Let an issue opt out**, e.g. `"diagnostic_symptom": true` in `match.json`, or a
   `--no-feature-check` flag on `run`/`bisect`. Cheap, explicit, auditable — and the trigger
   for setting it ("my symptom is an error message") is easy to state in `SKILL.md`.
3. **Anchor the markers.** `use of undeclared identifier` for a *user* symbol is feature
   absence; for a **built-in intrinsic** it is a diagnostic bug. `no matching function for
   call to` is not a feature-absence signal at all — a release predating a feature does not
   have a partially-matching overload set for it; `use of undeclared identifier` /
   `unknown type name` / `no member named` already cover that case. Direction A's misfire
   comes entirely from that one marker and it may simply not be earning its place.

Whatever is chosen, **the demotion should be recorded rather than silent.** Today an
`invalid-probe` header does not say which marker caused it, so reconstructing the reason
requires re-reading `classify()` against the captured text — which is the whole content of
`manual-case-classifier-branches.txt` and should not have needed to be hand-built. Stamping
`# invalid-probe-reason: matched marker "…"` into the header would make it self-explaining and
falsifiable.

### Artifacts left behind

`probe-freefn-good-diagnostic.hlsl` + `match-methodology-freefn.json`, and
`probe-arity-undeclared.hlsl` + `match-methodology-arity.json`. Both `match-*.json` `note`
fields state plainly that they are **not** predicates for #3055.

Both are captured `--expect invalid-probe`, and that declaration needs reading with care.
It asserts only *what the runner returns*, which is the finding and is true. It does **not**
carry the meaning the `--expect` option documents — "a control that is expected to be rejected
before it reaches the code under test" — because dxc compiled both shaders and diagnosed them.

That gap is itself a tooling observation worth promoting. The honest expectations are
`no-match` and `repro` respectively; declaring either leaves a permanently-failing assertion
for every future `reindex`, which is noise a fresh collation session cannot distinguish from
sloppiness. Declaring `invalid-probe` passes, but only by borrowing a header whose documented
rationale is false here. There is **no value meaning "the classifier is expected to get this
wrong"**, and `audit` requires *some* value — it exits 1 on a variant with no `# expect:` — so
the choice is forced. A fourth value (`--expect known-misclassified`, say), or simply allowing
`--expect` to be waived with a recorded reason, would let a measured tooling defect be pinned
without either lying or failing.

Upside of the current arrangement: if the classifier is fixed, `reindex` will flag both lines.
That is correct behaviour — the right response is to retire these probes — and it is noted in
each `match-*.json`.

---

## 2. `text_stale` has no way to express a stale *comment*

`text_stale` is defined as the issue's **title or body** no longer describing what the
compiler does. #3055 does not qualify: the body is accurate, verbatim, including its quoted
output.

But the thread reads: body (reproduces) → 2023-07-14 `llvm-beanz`, "the code provided here
compiles successfully now" → 2023-09-27 `pow2clk`, "Exampled updated". The body was **edited
after** that comment, so a reader going top-down meets a maintainer saying it compiles, three
comments above a body that does not. That produces exactly the wrong conclusion `text_stale`
exists to prevent — "cannot reproduce" — and the field cannot record it, so it reaches nobody
except through this issue's own prose.

Two things follow, both for collation:

- Consider widening `text_stale` (or adding a sibling) to cover a superseded comment.
- More generally: **an edited issue body silently invalidates the comments above it.** This is
  the second time `issue.json` has earned its keep for a reason other than the one the README
  gives; here what is needed is not just a snapshot of the text but the knowledge that the
  text *moved*. `gh issue view` does not expose the edit history, but a comment saying "example
  updated" is a reliable tell and worth treating as a prompt to check which example the earlier
  comments were talking about.

---

## 3. Small things

- **`--linear` was worth it here even though the answer was flat.** `bisect` short-circuited
  after two endpoints; the linear scan confirmed all 20. SKILL.md already says to use
  `--linear` when the history mentions a fix — #3055's does, but for a *different example*,
  which is a case the rule does not obviously cover and did in fact warrant it.
- **The FXC pane needs a control too.** SKILL.md's control discipline for comparison panes is
  written entirely about Clang ("A Clang error is not evidence until you have a control"). The
  same reasoning applies to FXC, which is a different compiler with different gaps; the
  control is one extra API call and is captured in `manual-case-compiler-explorer.txt`.
- **`godbolt` records only the first line of each pane.** For `hlsl_clang_trunk` that line is
  `clang: warning: argument unused during compilation: '-Qembed_debug'` — so the tool's own
  summary shows nothing of the finding, and the verification the skill demands has to be
  redone by hand. Capturing the full per-pane output alongside the short link would close the
  gap between "verified before it is handed over" and "verifiable afterwards".
- **PowerShell trap, not a tooling defect:** `$args` is an automatic variable inside a
  PowerShell function, so a parameter named `$args` silently binds to nothing. A first attempt
  at the CE probes sent empty `userArguments` and dxc answered `Target profile argument is
  missing` — which reads exactly like the repro being wrong. Same shape as the `invalid-probe`
  trap one layer out: check that every input to a negative actually resolved (SKILL.md
  step 11).
