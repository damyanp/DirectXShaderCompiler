# Method notes -- #5194

**`reviewed_by` deliberately left blank in `verdict.json`.** Per this batch's
explicit instruction, `reviewed_by` is a batch-level field (SKILL.md: "Two
things belong to the batch, not the issue ... `reviewed_by` (step 10 runs
once over all the drafts)") and stays pending until the batch-019 collation
pass stamps it. That does not mean step 10 was skipped for this draft: a
separate agent running a different model (gpt-5.3-codex, via the `task`
tool) reviewed `comment.md` against `notes.md` for concision and unsupported
claims before this write-up was finalised, its findings are below, and the
accepted ones are already applied to `comment.md`. Whoever runs batch
collation should still record the reviewer identity in `reviewed_by` (this
session could not, by design) rather than leave the field silently empty.

Reviewer findings (gpt-5.3-codex), all four applied except as noted:

1. **Accepted, with a stronger fix.** Flagged "every release from v1.6.2112
   ... through the latest (v1.9.2607) reproduces it" as an unsupported
   universal claim. Correct catch: `bisect` short-circuits once both
   probeable endpoints agree, so only v1.6.2112 and v1.9.2607 were actually
   probed, not every release between them. Reworded to attribute the claim
   to `bisect`'s reported boundary rather than asserting every release was
   individually tested.
2. **Accepted.** "error exactly as reported" -> "still error" (concision,
   no information lost -- the quoted block below it already shows the
   match is exact).
3. **Accepted.** Trimmed the preamble sentence introducing the Clang pane
   ("since that's what @llvm-beanz's comment above points at").
4. **Accepted.** Cut "it just hasn't landed in a DXC release" as an
   interpretive/roadmap-adjacent claim beyond what was measured.

One reinforcement of an existing lesson, from finding 1:

- **Scope-creep in a bisect summary is easy to introduce even when the raw
  `notes.md` measurement is scoped correctly.** The first `comment.md` draft
  said "every release from v1.6.2112 ... through the latest (v1.9.2607)
  reproduces it", which overclaims: `bisect` short-circuits once both
  probeable endpoints agree, so only v1.6.2112 and v1.9.2607 were actually
  probed, not every release in between. `notes.md` already stated this
  correctly ("bisect checked both probeable endpoints ... short-circuited");
  the step-10 reviewer (gpt-5.3-codex) caught the drift in the compressed
  comment and it was corrected to "bisect reports always-repro'd from ...
  through ...". This is the same failure mode SKILL.md already documents for
  #3768 ("unchanged since 2019" from endpoints-only testing) -- it just
  recurred in a fresh draft, which is worth noting as evidence the lesson
  needs to stay in the reviewer's brief rather than being considered "solved"
  by having been written down once.
