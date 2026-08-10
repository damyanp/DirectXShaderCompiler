# Method notes from #6727

For collation to promote (or reject). Nothing here edits `SKILL.md` or
`scripts/triage.py`.

## 1. `godbolt-note.txt` can *manufacture* the very token an absence claim says is missing — and I wrote that bug before catching it

`SKILL.md` already warns that the banner is compiled and lands in
`!dx.source.contents`. What it does not say, and what nearly shipped here, is
the sharper form of the rule:

> **Never write into the banner a literal string that the note claims is absent
> from the output.**

My first banner said "no `dx.op.binaryWithTwoOuts` in the DXC panes" and spelled
the token out. CE compiles DXC with debug info by default — no `-Zi` in my
pane arguments, yet `!36 = !{!"/app/example.hlsl", !"// ...banner..."}` appears
in both DXC panes. So the published evidence for "this string never appears"
contained that string, in the pane's own output, six lines from the disassembly.
A reader Ctrl-F'ing the pane finds it and concludes the opposite of the finding.

Present-tense quotes (`udiv`, `urem` — claimed *present*) are harmless; the
asymmetry is specific to absence claims. The replacement banner names the ops by
opcode number, says why the class name is deliberately omitted, and warns the
reader that the banner itself is inside the metadata. Verified after
re-publishing: `shortlinkinfo` source no longer contains the token.

Suggested wording for `SKILL.md` step 7, one line: *"If the note asserts a token
is absent from the output, that token must not appear in the note."*

## 2. The same mechanism is usable *deliberately*, and it solves the hardest control problem an absence predicate has

An absence predicate has a control problem the existing guidance does not
answer: you can prove it is not vacuous (a shader missing the anchors), and you
can prove a failed compile does not satisfy it (a syntax-error shader), but
neither shows the `not_regex` clause can **ever** fire. Until it can, "the token
is absent" is unfalsifiable rather than measured, and a typo'd regex passes every
control you have.

`-Zi -Qembed_debug` on a copy of the repro whose *comment* contains the literal
token makes it fire, without modifying the compiler or hand-editing a capture:
DXC echoes its own input into `!dx.source.contents`, the token reaches the
output text, the predicate stops matching. Captured here as
`variant-control-token-visible-main-debug.txt`, `--expect no-match`.

This is cheap, general to every `not_contains`/`not_regex` issue, and worth
having in `SKILL.md` step 4 beside the existing two control shapes.
`manual-case-clause-table.txt` shows the resulting 4x4: each control flips
exactly one clause, which is the property that makes a control informative.

## 3. A "the compiler cannot do X" verdict is an evidence-tier question, not a probe

Three tiers, and only the top two are worth much:

1. **the intrinsic table has no entry** (`utils/hct/gen_intrin_main.txt`) and
   **`git grep OpCode::X` finds no emitter** outside one known component. This is
   what actually settles it.
2. **a contrasting compiler that does it from the same source** — FXC reaching
   the two-output `udiv` here. Converts "DXC lacks a feature" into "the
   capability exists and DXC's front end cannot reach it", which is a different
   and much more actionable claim.
3. **one shader that does not produce X.** Nearly worthless alone; it is
   vacuously true of almost any shader.

Feature-request triage that stops at tier 3 will look identical whether the
answer is right or wrong. Worth saying explicitly in the `enhancement-not-bug`
context, because the tooling only automates tier 3.

## 4. A dead lowering-table entry made "unreachable" briefly look like "already supported"

`grep OpCode::UMul` returns
`{IntrinsicOp::IOP_umul, TranslateMul, DXIL::OpCode::UMul}` in
`lib/HLSL/HLOperationLower.cpp` — the HLSL lowering table, naming the exact
opcode the issue says is unreachable. Read alone it says the feature is wired
up. `TranslateMul` never reads its `opcode` parameter; the entry is dead.

Generalisation: **an intrinsic-to-opcode table entry is not evidence that the
opcode is emitted.** Read the translator body before believing the table. Cost
here was a few minutes; on an issue that concluded from the table alone it would
have been a confident wrong `does-not-repro`.

## 5. `--linear` is worth its cost on an always-repro'd issue, for a reason unrelated to non-monotonicity

`bisect` short-circuited to `always-repro'd` after 2 probes, which is correct
and cheap. But the *claim a feature request wants to make* is "no shipped
stable compiler has ever had this", and two endpoints do not support it — the
step-10 reviewer flags exactly that kind of quantifier. The linear scan (20
stable releases, mostly cache hits from parallel workers) turns an inference
into a count.

Suggested framing: reach for `--linear` when the write-up needs a **population
claim** ("none of N releases"), not only when the history might be
non-monotonic.

## 6. The count that goes in the draft is not the count `bisect` printed

`bisect --linear` listed 20 stable releases; a separate `v1.5.2003` prerelease
probe made **21** `out-v*.txt` files. My first draft said "all 20 releases ...
including v1.5.2003", double-counting the hand-run probe. The later user policy
adds a second distinction: because this issue does not explicitly name that
prerelease and has no `release-policy.json` opt-in, the public history count is
20 stable releases even though 21 files exist. Count files to audit the
arithmetic, then state which population policy the claim uses.

## 7. Reading the issue's cross-reference timeline paid better than any search

`gh api .../timeline` (already prescribed for the anti-cross-reference check)
surfaced the two most useful facts in the triage as a side effect:
`microsoft/DirectXShaderCompiler#4612`, a duplicate user request closed into
this issue, and `llvm/llvm-project#128638`, an open 2025 LLVM issue whose text
independently reaches the same conclusion this triage measured. Neither is
findable by searching this repo.

Worth promoting from "run it before the batch report" to "run it in step 1",
with `--jq` including `.source.issue.repository.full_name` — without that field
the entries render as bare `#4612` / `#128638` and read as issues in this repo,
which for `#128638` is badly misleading.

## 8. Small tool observations

* `triage.py run --compiler <release-tag>` works for a release outside the
  bisectable sequence and writes a normal `out-<tag>.txt` probe. Use that only
  when the issue explicitly names a prerelease; being current at filing is not
  enough under the standing policy. A tool-written capture remains preferable
  to an ad-hoc one because `reindex` can re-score it.
* `triage.py labels --issue N` prints `proposed + -` with nothing after it when
  no proposal has been recorded yet. It reads like "no labels are proposed" from
  an analysis rather than "you have not written one". Not a defect, but the
  first read is misleading.
* The `grep` tool's silent zero-result failure (documented in `SKILL.md`) was
  avoided throughout by using `git grep` and `Select-String`. Every absence claim
  in `notes.md` came from one of those two.
