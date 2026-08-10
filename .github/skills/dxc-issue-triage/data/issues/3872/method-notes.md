# Method notes — from triaging #3872

Things that generalise beyond this issue. `SKILL.md` and `scripts/*.py` were not modified;
these are for whoever collates the batch.

## 1. The self-test clause is not ceremony — it caught a false regression here

`SKILL.md` already requires a positive self-test in an absence predicate. What this issue adds
is a *worked failure*: the self-test did not merely reassure, it overturned a bisect result.

`bisect --linear` first reported `v1.4.1907 no-repro` and everything from `v1.5.2010` onward
`repro`, i.e. "introduced in v1.5.2010". That is a tidy, plausible, completely wrong story. The
clause matrix showed the `1.4` column matching every *acceptance* clause and failing every
*signature-row* clause — including the row clause on `VSOut`, the position nobody disputes. The
2019 disassembler prints `NONE` in the SysValue column where today's prints `SHDINGRATE`; the
compiler's classification is identical in both, as the unchanged
`!{i32 1, !"SV_ShadingRate", i8 5, i8 29, ...}` metadata and the identical feature banner show.

Two rules worth promoting:

* **A self-test clause must be checked per release, not only on the current build.** Its whole
  value is that it fails on the release where the instrument, not the behaviour, changed. A
  self-test that is only ever evaluated on `main-debug` is decoration.
* **When a self-test fails on a release, the correct reading is "this predicate cannot be
  evaluated here", never "no-repro".** The tool cannot make that distinction; only the matrix
  can. Consider whether `bisect` could report `self-test-failed` as a third state — currently a
  clause that is diagnostic of a broken instrument is scored identically to one that is
  diagnostic of a fixed bug.

The remedy that worked: an **instrument-portable twin predicate**
(`match-portable.json`) with the same structure but a version-tolerant anchor, bisected
separately. `always-repro'd across v1.4.1907..v1.9.2607`. Keeping both is better than replacing
one with the other — `match.json` is the sharper measurement of today's build, and the twin is
the one that can be carried across a decade of disassembler churn.

## 2. Anchoring clauses inside a single `$ dxc ` block of a multi-invocation `cmd.txt`

A five-line `cmd.txt` produces five concatenated blocks in one capture, each shaped

```
$ dxc <args>
[exe] <path>
[exit] <rc>
--- stdout ---
...
```

A bare `contains` on such a capture cannot say *which* compile did the thing, which for a
per-signature-point issue is the entire question. The pattern that worked, given that
`_eval_match` uses `re.MULTILINE` only (so `.` never crosses lines):

```
^\$ dxc -T hs_6_4 -E HSCPInMain (?:(?!^\$ dxc )[\s\S])*?^; Input signature:(?:(?!signature:)[\s\S])*?^;\s+SV_ShadingRate\s+...
```

`(?:(?!^\$ dxc )[\s\S])*?` is a gap that cannot cross into the next command's block;
`(?:(?!signature:)[\s\S])*?` is a gap that cannot cross into the next signature section. Both
are lazy, so the anchors bind to the nearest following section.

**Do not pin the source filename in the block anchor.** `run --shader <control>` retargets the
filename on every line, so a control run would then fail to match for a reason that has nothing
to do with the control. Use `[^\n]*` where the filename goes. The variable part of a control
should be its *content*, not the shape of its capture.

Related: `run --shader` retargets **every** line of a multi-line `cmd.txt`, so every control
shader must define all five entry points. That constraint shaped all three controls here and is
worth knowing before designing them.

## 3. Choosing the disassembly token to anchor on

Two `SV_ShadingRate` rows appear in one pane of output — the container signature table and the
PSV runtime-info copy. They differ in their third column: the first prints the SysValue name and
a format (`SHDINGRATE ... uint`), the second prints the interpolation mode
(`nointerpolation`). Anchoring on the SysValue token plus the trailing format column makes it
impossible to match the wrong table.

Better still: **check whether a committed FileCheck test already anchors on the same token.**
`tools/clang/test/HLSLFileCheck/hlsl/semantics/sv_shadingrate/shadingrate1.hlsl` pins both
`1SHDINGRATE    uint` and `!"SV_ShadingRate", i8 5, i8 29,`. Reusing a token the project's own
tests rely on means the anchor is as stable as the test suite, and it takes one search to find.

## 4. Missing-diagnostic issues have two gates, and they may share a table

"The compiler accepts it" and "the validator accepts it" are different claims with different
severities, and the `validation` label (live description: *"Related to validation or signing"*)
is about the second. Both were measured here, and the interesting part is *why* they agree:
`CGHLSLMS.cpp`, `HLSignatureLower.cpp` and `DxilValidation.cpp` all resolve through
`SigPoint::GetInterpretation`. One table, three consumers.

Worth doing in general on a missing-diagnostic issue:

* run the standalone validator (`dxc -Vd -Fo` then `dxv <container>`) rather than relying on
  `dxc`'s in-process validation alone — but **say plainly that it is the same code**, so the
  reader does not count it as a second witness;
* give the validator arm a positive control that fails for an *unrelated* reason. A root
  signature that does not cover its SRV works in every stage and cannot be confused with the
  semantic under test. Without it, "validation succeeded" is unreadable — the front end rejects
  `NA` cells *before* a module reaches the validator, so the validator rule under discussion is
  nearly unreachable from HLSL and would look silent whether or not it worked.

## 5. Controls for a cross-compiler pane: use `-D` to make an A/B in one file

CE panes share a single source, which makes "same file, one thing changed" awkward. A
preprocessor guard solves it: put the construct under `#ifndef NO_RATE`, and add a control pane
with the identical compiler and flags plus `-DNO_RATE`. Exit 0 there and exit 1 without it is a
one-variable experiment inside the constraint that CE imposes.

This mattered: the first attempt used "compile the compute entry point" as the Clang control,
which failed — Clang parses the whole translation unit, so the struct's semantic was diagnosed
regardless of which entry point was selected. The control was measuring the wrong thing and
looked like a broken pane. `-DNO_RATE` fixed it in one line.

Also: **a stage-specific issue may still have a controllable cross-compiler question**, just a
narrower one. Clang cannot be asked about hull/domain control-point signatures, but it can be
asked whether it knows the semantic at all (`unknown HLSL semantic 'SV_ShadingRate'`), and that
answer was directly relevant to a maintainer comment on the issue. Publishing a *smaller,
separate* source for that pane, and keeping the stage-accurate repro local, is better than
either publishing noise or skipping the question.

## 6. Check an FXC pane's *reason* before drawing a contrast from it

FXC rejected the repro — and rejected it in the vertex shader too, the one position the spec
permits, because the semantic postdates Shader Model 5.1 by three shader models. A pane that
would reject correct and incorrect code identically carries no information. The control pane
(same file, `/DNO_RATE`, compiles fine) is what made that legible rather than a guess.

Generalisation: for any semantic or feature gated on a shader model above 5.1, an FXC pane can
only ever say "FXC is old". Establish the feature's shader model first; if it is > 5.1, do not
include the pane, and record the measurement somewhere so the omission is evidence-based.

## 7. `triage.py godbolt` overwrites `manual-case-godbolt-verify.txt` on every run

Only the last link's panes survive. Exploratory runs — a Clang probe, an FXC probe — need their
output copied to a differently named `manual-case-*.txt` immediately, with the command that
produced it and its own shortlink in a header, or the evidence is lost on the next invocation.
Three runs were needed here (Clang probe, FXC probe, published link) and the first two would
have vanished.

Possible tool improvement for collation to consider: name the verify file after the source or
accept an explicit output name, so probes do not collide with the published link.

## 8. `ce_args` takes only the first line of a multi-invocation `cmd.txt`

It warns, but the consequence is easy to under-react to: for this issue line 1 is the *self-test*
(the spec-legal `VSOut` case), so an unexamined link would have shown a reader the one compile
nobody is arguing about. Any issue with a multi-line `cmd.txt` needs explicit `id:<args>`
overrides for every pane. Worth treating the warning as an error in practice.

## 9. Distinguish the reporter's assertion from the reporter's question

This report asserted four table cells were wrong and separately asked about a fifth. Folding the
question into `match.json` would have made the predicate unfalsifiable — a matching capture
would have "confirmed" something nobody claimed. Keeping it as a separate probe with its own
predicate (`probe-gsvin.hlsl`, `match-gsvin.json`) preserved the distinction, and the predicate's
`note` says in as many words that a match there is not a defect finding.

## 10. Small operational traps

* The agent `grep`/ripgrep tool silently returns "No matches found" for everything under
  `.github/` (dot-directories are skipped by default) and the false negative is indistinguishable
  from a true one. `Select-String` throughout.
* `Get-ChildItem -Recurse` over `lib` and `tools/clang` piped to `Select-String` takes ~90 s.
  Narrow the path first; `Select-String -Path <specific file>` is instant.
* `triage.py run --args` replaces the entire argv, so the source filename must be repeated in it;
  `--args`/`--shader` and `--label` are mutually required.
* Exit code `2147500037` is `0x80004005` (`E_FAIL`) — an ordinary diagnosed error, not a crash.
* `create` refuses to overwrite an existing file; rewriting a predicate wholesale needs an
  explicit delete first. Minor, but it interrupts a "regenerate the file" habit.
