# Method notes — issue 4763 (batch-017)

Reusable lessons for collation. Findings live in `notes.md`; this file is only about how
the measurement was made and where it nearly went wrong.

## 1. An absence-shaped symptom inverts the classic hazard — in a direction nobody warns about

4763 is a **missing-diagnostic** issue, so "the bug is present" means "the compiler stayed
silent". The standard warning is that a bare `not_regex error:` predicate is satisfied for
free by any release that failed to compile for an unrelated reason, turning a failure into
a fake reproduction.

Fixing that by composing the predicate with compile-success anchors (`all_of` of
`^define void @PSMain\(\)`, a binding-table line, a layout line, *then* the absence clause)
does remove the fake-reproduction failure mode. But it installs a new one in the opposite
direction: **a release that cannot compile the shader now scores `no-repro`, which reads as
"fixed".** For a bug whose whole point is silence, "fixed" is the more dangerous error,
because it invents a fix commit that does not exist.

So the anchored predicate is necessary but not sufficient. The companion that makes it safe
is an **independent per-release record that the shader actually compiled** — here
`release-matrix.py`, which ran five sources against each of the 20 cached releases and
recorded exit code and diagnostic count for each. Without that matrix, every `repro` and
every hypothetical `no-repro` in the bisect is unfalsifiable.

Generalisation: for any absence-based predicate, budget for two artifacts, not one — the
predicate, and a separate proof of successful execution on every point probed.

## 2. A positive control is what converts "silent" into "silent *about this*"

`control-cbv-array.hlsl` (`ConstantBuffer<T> cb[4]`) is diagnosed on **every** release
probed, `exit=0x80004005`, exactly one diagnostic:
`error: object types not supported in cbuffer/tbuffer view arrays.`

That single line does more work than the entire bisect. It rules out "this DXC build emits
no diagnostics at all", "the harness is swallowing stderr", and "the profile/args are wrong"
simultaneously, on the same instrument, on the same release. A missing-diagnostic triage
without one of these has established almost nothing.

Note also that `0x80004005` is `E_FAIL` for an **ordinary diagnosed error**. It is not
crash-shaped and must not be routed to `internal_failure`.

## 3. Instrument portability: the disassembly is a different language on old releases

Two spellings changed under the probe and both were nearly used as anchors:

* Layout struct prefix: `%hostlayout.__cbModelData2` on current builds vs
  `%dx.alignment.legacy.__cbModelData2` on v1.4.1907. `hostlayout` was the first instinct
  for the acceptance anchor. It would have scored the oldest release `no-repro` and
  manufactured a regression boundary that does not exist.
* v1.4.1907 prints the resource member *inside* the cbuffer layout block
  (`float3 h; ; Offset: 0`); current builds omit it entirely.

The habit that catches this: before finalising any predicate, run it by hand against the
**oldest** cached release, not just the newest, and read the raw output rather than the
verdict. Prefer anchors on things the *language* guarantees (a function definition, a
binding-table row) over things the *printer* chooses.

## 4. Put a self-test clause inside the predicate

`match-layout.json` includes a clause asserting the resource-free control cbuffer reads
`Size: 4` at offset 0. It is not part of the symptom; it exists so that a release whose
disassembler formats layouts differently fails *that* clause too. A no-match then reads as
"unmeasurable on this instrument" rather than "fixed here", from the capture alone, without
re-running anything. Cheap, and it survives into the archive.

## 5. `--hypothesis` is the right tool for checking someone else's claim — and it caught a real error

A comment on the issue claimed a 0-size resource nested in a struct still 16-byte-aligns the
following field. Source reading (`AlignBaseOffset` returns the base offset untouched for
resource types) suggested it was wrong, and a draft of `comment.md` said so publicly.

Measuring it refuted the draft, not the comment: the early-return applies to the resource
type, not to the enclosing struct-typed field, which takes its normal 16-byte alignment.
`variant-resource-in-nested-struct.hlsl` + `match-nested-align.json --hypothesis --expect
match` recorded `hypothesis supported`, and the variant compiles its own no-inner-struct
control in the same run so the comparison is same-instrument.

Two transferable rules:

* **Never publish a correction of another person's claim from source reading alone.** The
  cost of being wrong is borne by them, in public, years later.
* When the claim is about a *different construct* from the repro, build that construct. It
  took one shader and one run, and it changed the draft from wrong to additive.

## 6. Date the mechanism by measurement, not by `git log` alone

`git log -S` located both the commit that made resource-in-cbuffer legal (2017) and the
commit that added the zero-size rule with `!IsHLSLStructuredBufferType(Ty)` (2021). Rather
than assert the consequence, a **supplementary inverted predicate**
(`match-buffer-legacy.json`) detected the *pre-fix* `Buffer<T>` sizing and bisected it:
present ≤ v1.6.2104, gone from v1.6.2106 — exactly straddling the commit date. The code
reading and the release behaviour now corroborate each other.

Two cautions when doing this:

* Give the inverted predicate a loud `note`. Its bisect prints `repro`/`no-repro` in the
  same format as the real one, and `repro` there means "old behaviour still present". A
  collator reading only the transcript will otherwise import a spurious history.
* Its `result:` line said *non-monotonic history … transitions at v1.6.2106*. That is the
  tool describing an inverted-polarity predicate correctly; it is not a claim about 4763.

## 7. Separate the reporter's asks before writing the predicate

The title asks for a diagnostic; the body's table is about layout. They resolve
*differently* — the diagnostic turns out to be a deliberate 2017 design decision, the layout
is a plain bug with a precedent fix. One predicate covering "the issue" would have averaged
two different answers into one wrong one. `expected.md` split them (Ask A / Ask B) before
anything ran, and each got its own predicate and its own history.

Corollary: `match.json` (Ask A) is knowingly coupled to Ask B's layout signature, because on
the reporter's exact shader the unused buffers are dropped and the space they left is the
only portable evidence of acceptance. That coupling is recorded in the file's `note`. A
future release that both diagnoses *and* changes the layout flips two clauses at once and
must be read from the capture, not inferred.

## 8. Small tooling facts worth passing on

* `triage.py` exposes **`con()`** for the DB connection, not `db()`. Anyone writing a matrix
  script over `releases.cached_path` will hit this in the first minute.
* `godbolt` refuses to publish cleanly if a generated artifact is sitting in the issue
  directory — it warned `repro references local file(s) ['test-asfiled.h']`, which was a
  leftover `-Fh` output, not a real include. Clean generated binaries before publishing.
* `godbolt` auto-archives the previous pane text under a content-hashed filename when re-run,
  so republishing does not lose the earlier verification.
* Compiler Explorer's `dxc_1_6_2112` pane emits `warning: DXIL.dll not found.` — an
  environment artifact of CE, not of the shader. It would trip a `warning:`-based absence
  clause if CE panes were ever scored. Local probes had `dxil.dll` present and emitted zero
  diagnostics; the matrix is the evidence for that, not the CE pane.
* A `-fsyntax-only` Clang pane can be **self-controlling**: its own unrelated
  `-Wimplicit-int-float-conversion` warnings, at the right columns, prove Sema resolved the
  members it is being asked to stay silent about. Cheaper than adding a separate control
  compile, and it lives in the same screenshot.
* `catalog --seed-from build/tools/clang/test/dxc_releases` was deliberately **not** re-run:
  both cache roots were already reconciled and all 20 stable releases had a `cached_path`.
  It writes shared state, and other workers were running concurrently.
* `reindex` was never run, per the batch rules; `audit --issue 4763` was used for the
  completeness check instead.

## 9. Mistakes made in this triage

1. Drafted a public correction of a commenter's alignment claim from source reading. Refuted
   by measurement before it shipped (§5).
2. Chose `%hostlayout.` as the acceptance anchor before probing the oldest release (§3).
3. Published a Compiler Explorer link whose banner said "All three panes" while four were
   published; rewrote `godbolt-note.txt` and republished, then verified the replacement via
   `GET /api/shortlinkinfo/<id>` rather than by eye.
4. Used `triage.db()` in `release-matrix.py`; the accessor is `con()` (§8).
5. Invented a plausible-looking `#issuecomment-` permalink from memory when drafting, and in
   the same draft named the Compiler Explorer panes from memory as "dxc trunk / v1.7.2308 /
   v1.6.2112 / clang trunk" when the published link actually carries `fxc_10_0_19041`,
   `dxc_1_6_2112`, `dxc_trunk` and `hlsl_clang_trunk`. Both were caught by reading
   `issue.json` and `manual-case-godbolt-verify.txt` rather than trusting recall. **Every
   identifier that will appear in a public comment — permalinks, pane names, version
   strings, offsets — must be copied out of a captured artifact, not typed from memory.**
   The FXC pane was the most valuable one in the link and the draft omitted it entirely.
