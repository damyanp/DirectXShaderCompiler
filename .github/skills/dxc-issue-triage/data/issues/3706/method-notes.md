# Method observations — #3706 (batch 009)

For collation to promote or discard. Nothing here was written to `SKILL.md` or `scripts/`.

## 1. The #3009 structural-undef trap is enforceable from source, not just observable

SKILL.md documents the trap empirically ("`bufferStore`'s unused coordinates are `undef` for
non-structured buffers"). While triaging this issue the *rule* behind it turned up in
`lib/DxilValidation/DxilValidation.cpp` (`RawBufferLoad`/`RawBufferStore` cases): for
`ResourceKind::RawBuffer` the validator **errors if the elementOffset operand is not `undef`**
(`InstrCoordinateCountForRawTypedBuf`), and for `StructuredBuffer` it errors if it **is**
(`InstrCoordinateCountForStructBuf`).

That converts "some ops carry structural undef" from a caution into a checkable fact: for any
DXIL op the trap is worth suspecting, `git grep isa<UndefValue> lib/DxilValidation` names the
operand positions where `undef` is required or forbidden. Cheaper and more reliable than
discovering it by having a control fire.

## 2. A negative control claimed in a predicate note but never captured

`data/issues/3009/match.json` says *"Verified against a control (the same shader with b.y also
assigned), which must NOT match."* There is no such shader in `data/issues/3009/`: the three
`.hlsl` files are the repro, the maintainer's variant and a compute restating, and both
captured variants carry `# expect: match`. `audit` does not catch this, because the claim is
prose inside a `note` and every `.hlsl` present does have a capture.

This is the #3038 defect (README: "the control had been run by hand … the evidence never
written down") recurring in a place the tooling cannot see. If it is worth checking, the check
is textual: a `note` that says a control exists should be required to name the file.

*(Reported for collation only — #3009 is not this session's directory and nothing in it was
modified.)*

## 3. `godbolt-note.txt` should not carry source line numbers

The banner is prepended to the published source, so every line number in the panes shifts by
the banner's length. A first draft said "It still diagnoses line 38" — accurate for that
banner, wrong the moment the banner was reworded (the same statement became line 48).
SKILL.md already warns that the banner is *compiled*; the line-number consequence is a second
instance of that and is easy to miss because the note reads as prose. Refer to the statement,
not the line.

Also: `annotate()` prefixes every line with `// `, so a note already written as C++ comments
is published double-commented (`// // What to look for`). Not harmful, but the first
`godbolt` run had to be discarded and re-published. One line in SKILL.md ("write the banner
as plain prose; the tool adds the comment markers") would prevent it.

## 4. A control pane can be self-controlling

SKILL.md requires a control before believing a Clang difference. Here the `-fsyntax-only`
Clang pane supplied its own: Clang emitted `-Wsign-conversion` on the *same statement* that
reads the uninitialised variable, which proves Sema reached that expression. When the symptom
is front-end silence, a diagnostic on the same line from an unrelated check is a stronger and
cheaper control than a separate trivial shader, because it rules out "the front end never got
there" for that exact expression rather than for the file in general.

## 5. `check-in-clang`'s description is an instruction, which makes it ambiguous as a finding

SKILL.md step 8 endorses labels that record *findings* ("the fix belongs in Clang"), and cites
`check-in-clang` in that spirit. Its actual description is *"See if this repros in clang as
well"* — a request for work. Proposing it in the same comment that reports the Clang result
is contradictory, so it was left out here and the result put in prose instead. #3009 proposed
adding it. Worth a house rule either way, because two issues in the same corpus now treat it
differently.

## 6. Two cheap checks that paid for themselves

- **Grepping every `out-*.txt` for `warning|error|not found|not signed` after the scan.** One
  command; it confirmed simultaneously that no release diagnosed the input, that none was an
  invalid probe, and that `dxil.dll` was present in all 20 release probes — the last being
  what licenses the claim that the validator accepted the module everywhere, which nothing in
  the exit codes says.
- **Running the validator-liveness control on a release as well as on ground truth.** It was
  added only to prove the validator is in the pipeline, and incidentally found that
  v1.4.1907 *accepts* an undef UAV store that v1.9.2607 and `main` reject. An unexpected
  result from a control that exists to prove the harness works is the cheapest finding
  available.

## 7. The brief's cross-issue framing worked, but note the tension with SKILL.md

SKILL.md tells a per-issue worker to leave cross-issue claims to collation and say so only in
`method-notes.md`. This brief explicitly asked whether #3706 is the same defect as #3009 and
offered `duplicate-of #3009` as an action, so the analysis went into `notes.md` — and the
answer turned out to hinge on a measurement (`-Wall` is silent on the partially-initialised
form) that only made sense to take while this repro was in hand. Collation reading two
finished directories could not have taken it. That is an argument for briefing the *question*
to the worker while keeping the *verdict* at collation, which is roughly what happened here;
the draft comment stays silent on #3009.
