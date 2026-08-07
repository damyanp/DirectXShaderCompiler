# #2673 — method observations

For collation to promote or discard. Nothing here was fixed in `SKILL.md` or `scripts/`.

## 1. `godbolt`'s verification step does not verify the symptom (tooling gap, concrete fix)

`cmd_godbolt` compiles on CE and prints `exit=<rc>` plus the **first non-empty line** of the
pane's output (`triage.py:1569-1573`). For this issue those lines were
`warning: DXIL.dll not found…` and `;` — neither says anything about the finding. SKILL.md
already warns that the summary shows only the first line and tells you to open the link, but
the link here is 500+ lines of DXIL and the symptom is one metadata node inside it, so "open
it" is a weak check and leaves nothing on disk.

The fix is small and uses code that is already there: `ce_compile` returns the full text and
`classify(issue, text, rc, timed_out)` is the same scorer used for local probes. Scoring each
pane and printing `-> repro | no-repro` beside `exit=` would make the CE claim mechanical, and
writing the scored text to `godbolt-<compiler>.txt` would make it re-checkable by `reindex`
like every other capture. As it stands, "the link is verified before it is handed over" is
only true for exit-code-shaped and first-line-shaped symptoms.

I worked around it with `data/issues/2673/verify-godbolt.py`, which imports `triage` and
re-runs `ce_compile` + `classify` over the published source. It works, but a per-issue script
is exactly the "control nobody can re-run" shape SKILL.md warns about — it should be a flag.

## 2. An anchor predicate inverts the meaning of `# verdict:` in its own captures

`match-defines-present.json` exists to separate "debug info emitted, no duplication" from "no
debug info at all" — the distinction the primary predicate cannot make on its own. But it is a
*good-state* predicate, so `# verdict: repro` in `out-main-debug--match-defines-present.txt`
means "the anchor held / this probe was capable of showing the symptom", not "the bug is
present". Anyone re-reading the tree — including collation — meets a capture header that reads
backwards unless they open the predicate's `note` first.

The pattern seems generally useful (SKILL.md's "anchor the predicate with a positive clause"
does not cover the case where the anchor has to be a *separate* measurement, because what you
want to know is why a `no-repro` happened). If it is kept, the vocabulary should distinguish
symptom predicates from validity predicates — e.g. a `"role": "anchor"` key that makes the
header say `anchor-held` / `anchor-failed` instead of `repro` / `no-repro`.

Not needed on this issue in the end: the anchor's regex is a strict prefix of `match.json`'s,
so every matching probe satisfies it by construction, and all 20 releases matched. It would
have mattered had any release scored clean.

## 3. Expand lit substitutions from `lit.cfg`; do not assume what `%dxc` is

SKILL.md warns about building a repro from a `RUN:` line (#3768's silent profile change). A
second, quieter face of the same trap: `%dxc` is a substitution, and it is free to add flags —
this test's own `CHECK` line expects `-Qembed_debug` in `!dx.source.args`, which looks exactly
like `%dxc` adding it. It does not (`tools/clang/test/lit.cfg:294` substitutes the bare
binary); dxc adds `-Qembed_debug` itself. Worth one grep before treating a RUN line as a
command, and worth a sentence in the step-3 warning.

## 4. "Run the in-tree test to see whether it still passes" is out of bounds, and that is fine

The obvious corroboration here — run lit on `share_mem_dbg.hlsl` — writes `Output/` directories
into the DXC tree, which violates the worker boundary (`data/issues/<nnnn>/` only). The same
question was answerable statically and more precisely: `lit.local.cfg` sets
`config.suffixes = []` for the whole `HLSLFileCheck` tree, so lit never runs it at all, and the
TAEF harness that does run it passes `nullptr, 0` for defines. Reading the harness beat running
it. Possibly worth a line in SKILL.md: when an issue's claim is about a *test harness*, read
the harness — running it usually writes outside the boundary and answers a vaguer question.

## 5. Minor

- `releases` has no `sort_key` column; ordering is by `build_date`. My mistake, not a defect,
  but the `status`/`sql` examples in SKILL.md never show the releases schema.
- `run --args … --label …` behaved exactly as documented and emitted no spurious warning; the
  `--label` guard against clobbering the primary capture is clear at the point of use.

## 6. Cross-issue

Nothing to claim. I was given one issue and know nothing about the rest of the batch; the draft
makes no cross-issue reference. One in-repo pointer for whoever fixes this, recorded in
`notes.md` rather than the draft: `share_mem_dbg.hlsl`'s `CHECK` lines already encode the
correct expectation, but the harness that runs them never exercises the driver path, so the
test does not guard against this defect and would need a command-line-driven case to do so.
