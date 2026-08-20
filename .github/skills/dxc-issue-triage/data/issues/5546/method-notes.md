# Method notes -- #5546

- This issue is not a crash/regression report; it's a `docs`-labelled request about an
  **external** page (learn.microsoft.com, backed by `github.com/MicrosoftDocs/win32-pr`, not
  this repo). The underlying technical premise ("`discard` doesn't skip subsequent
  statements the way an early exit would") is nonetheless fully compiler-verifiable via a
  simple controlled A/B (`discard` vs `return` inside an otherwise-identical `if`), so
  `not-compiler-verifiable` here describes the *deliverable* (an edit to someone else's repo),
  not the technical claim, which was checked and confirmed. Worth flagging for collation: a
  `docs` label and a `not-compiler-verifiable` status can coexist with high-confidence,
  compiler-backed evidence -- the two axes (whose repo owns the fix vs. whether the claim is
  measurable) are independent and neither should be inferred from the other.

- Fetched the live Microsoft Learn page during triage (2026-08-19) rather than relying on the
  2023 issue text, since a docs-clarity request can go stale in either direction (fixed, or
  reworded to no longer say what the reporter quoted). It hadn't changed (`updated_at:
  2025-03-11`, still lists `discard` under flow control). Recommend this as a standard step
  for any `docs`-labelled issue that quotes or links a specific page: check the live page
  before assuming the 2023-era quote still holds.

- Ran a different-model review of `comment.md` before finalizing (gpt-5.3-codex via a
  sub-agent), even though `reviewed_by` in `verdict.json` was deliberately left **empty**
  per this task's instruction and per `triage.py verdict`'s own message ("step 10 is a batch
  step; do not fill it in yourself"). The review caught one real factual error worth
  recording generally: the draft's shorthand list of the Learn page's flow-control bullets
  said "break/for/if/return/etc", but `return` is not one of the page's HLSL keyword bullets
  at all (the actual list is break, continue, discard, do, for, if, switch, while) --
  `notes.md` had the correct list, but the more-compressed `comment.md` line, written
  separately, introduced the error. This is the same failure shape `SKILL.md` already
  documents for `summary`/`text_stale` fields ("compression must only remove claims, never
  add one") -- it also applies to a draft's own inline shorthand of a quoted list, not only to
  the short verdict fields. Two more suggestions from that same review were rejected because
  they conflict with hard skill requirements (cutting the `[!WARNING]` draft banner and the
  AI-assistance disclosure trailer) -- both are mandated by step 9, and a concision-focused
  reviewer has no way to know that from the draft alone.
