# Method notes — #2331 (batch 006)

Observations about the *method and tooling*, not about the issue. Recorded, not fixed.

## Signing was a new code path, and here is where the tooling's assumptions did not fit

This was the first issue in any batch to exercise DXIL signing. Four mismatches:

### 1. There is no way to record "what the container looked like", only "what was printed"

Every predicate kind in `match.json` inspects **stdout/stderr and the exit code**. This issue
is titled for signing, and the honest way to answer "was it signed?" is to compile with
`-Fo`, read the 16-byte digest at offset 4 of the `DXBC` header, and compare. Nothing in the
runner does that, and there is no artifact type for "a fact measured from an output file".

Worked around by doing it by hand and writing `manual-case-signing.txt`, which is prose and
so is invisible to `audit`, to `overview.md`, and to any future cross-batch query. If
container-inspection issues become common (signing, reflection, `-Fre`, `-Fd`, root
signatures, `-Qstrip_*`), a `binary_probe`-shaped predicate or a first-class
`measurement-*.json` would be worth having. As it stands the *most decision-relevant table in
this triage* — the digest table — lives only in prose.

### 2. `--expect` is per-file, so a variant that flips meaning across the range is awkward

`case-four-enumerators.hlsl` is expected to `match` at v1.4.1907 (2019 behaviour, per the
body) and `no-match` from v1.5.2010 on. `run --expect` records one expectation per output
file, which is right, but there is no way to say "expected match up to X, no-match after" as
a single declaration, so the intent lives in 21 separate files and in prose. Both of this
issue's revised expectations (`variant-four-enumerators-main-debug.txt`,
`variant-four-enumerators-v1.4.1907.txt`) were changed through `triage.py expect`, the
sanctioned path; measurements were untouched.

### 3. `bisect --linear` has no notion of "and also run these other shaders"

The verdict-relevant finding here — the B1/B2 transition boundary — required running two
*extra* shaders across the same 20 releases. There is no command for that, so it was done
with a hand-written loop over `run`. It worked, and the outputs are filed as `variant-*`, but
"scan a second input across the release set" is common enough (it is how you date a
behaviour change that is not the reported symptom) that it might deserve support.

### 4. The environment question the brief raised is not one the tooling can answer

"Is there a `dxil.dll` next to each release binary?" had to be answered by listing the
release cache directories by hand, and "does this build consult it?" by reading
`lib/DxcSupport/dxcapi.extval.cpp` and by `git log -S` on a warning string that no longer
exists in source. `compilers` in `triage.db` has `(id, exe_path, git_commit, version,
built_at)` and nothing about the environment around the binary. Since a missing external
validator silently changes both the diagnostic wording *and* the exit code
(`0x80AA0009` vs `0x80004005`, and the source location disappears), that is exactly the sort
of difference that would invent a regression in a linear scan. It happens not to have here —
every cached release ships one and none printed the warning — but that is luck, not design.

## Predicate design

**A predicate keyed to the exit code would have been wrong.** With the external validator
forced via `DXC_DXIL_DLL_PATH`, the same failure exits `0x80AA0009`
(`DXC_E_IR_VERIFICATION_FAILED`) rather than `0x80004005` (`E_FAIL`). Rule text spanned both;
exit codes did not. `nonzero_exit` is the right amount of exit-code sensitivity.

**And a line-anchored text predicate would also have been wrong.** v1.4.1907 prints
`at 0x2324278c200 inside block #0 of function MainPS Instructions must be of an allowed type`
on one line; modern DXC prints `repro.hlsl:24:1: error: Instructions must be of an allowed
type.` plus a `note:`. Matching the *rule substring* is what makes one predicate span
v1.4.1907..main. Matching a whole line, or including `error:`, would have scored the oldest
releases `no-repro` and reported a regression that does not exist.

Both controls (`control-default-case.hlsl`, `control-enum-minimal.hlsl`) are named in
`match.json`'s `note` and were run at the floor, at the head, and on ground truth. The second
also serves as feature-presence evidence, which is worth generalising: for any pre-2020
issue, a control that proves *the language feature existed at the floor* converts a possible
`invalid-probe` into a known result.

## Compiler Explorer

* `godbolt` prints `CE args: <the default from cmd.txt>` even when every pane carries an
  `id:<args>` override. The overrides *are* sent — verified by reading back
  `/api/shortlinkinfo/<id>` — but the summary line implies otherwise and would mislead anyone
  checking a published link against its console output.
* `godbolt` reports only the **first non-blank line** of each pane. For `hlsl_clang_trunk`
  that line is `argument unused during compilation: '-Qembed_debug'`, which hides an
  exit-1 `fatal error: error in backend`. A pane can look fine and be broken.
  `ce-probe.py` (kept in this directory) POSTs to `/api/compiler/<id>/compile` and prints
  stdout, stderr and asm in full; it is what made the clang investigation possible.
* **`godbolt-note.txt` must not contain `//` comment markers.** `annotate()`
  (`scripts/triage.py:1420-1433`) prefixes every line with `// ` itself, so a note written as
  C++ comments publishes as `// // What to look for`. Published, saw it, rewrote, republished
  — the first link (`WGoj357v3`) is superseded and should not be quoted. Worth a line in the
  skill, since the failure is invisible unless you read back the shortlink.
* Reading back the shortlink (`/api/shortlinkinfo/<id>`) is a cheap and complete verification
  — language, pane ids, per-pane args, and the exact source. It caught the double-comment.
  Recommend it as the standard step-7 check.

## A trap of my own making, worth recording

Checking whether clang's DXIL output still contains `unreachable`, a naive
`'unreachable' in <whole CE response>` says **True** — because `!dx.source.contents` embeds
the HLSL source, and the source was a file whose *header comment* explains that it is testing
for `unreachable`. The IR body has none. **Grep the function body, not the module**, and
beware that DXC embeds your comments in the output it is being asked about.

## Boundary / concurrency

* `labels --refresh` does `DELETE FROM labels` followed by re-insert (`triage.py:1253-1256`).
  With several agents working concurrently that is a brief window in which another agent's
  `labels` read returns nothing. The cache had been refreshed the same day
  (`MAX(fetched_at)` = 2026-08-07), so `--refresh` was skipped and the live taxonomy read
  from cache. If concurrent batches are the norm, `labels --refresh` might be better as an
  upsert.
* Step 8's guidance in SKILL.md says `validation` means "**DXIL validation** specifically,
  not 'the compiler should validate this'". The **live description is broader**: *"Related to
  validation or signing"*. Both readings include this issue, so nothing turned on it, but the
  skill's paraphrase of a live label description is itself the kind of thing that goes stale
  — the skill is right that you must read the description, including when the skill quotes it.

## Cross-issue observation (kept out of the draft, per instruction)

@llvm-beanz's 2024 comment refers to an issue he filed against Clang to remove these
instructions during DXIL lowering. It is not linked from #2331 and was not searched for here.
If clang's behaviour on the cut-down form (no `unreachable`; `poison` into the phis) is that
work having landed, then #2331's disposition depends on that issue and linking them would
help; someone with the number should check. `comment.md` says only what was measured.

## PowerShell / environment friction

* A helper function named `H` collides with the built-in `Get-History` alias.
* `2>&1` cannot be appended to a `foreach` block.
* `Set-Location` inside a chained command does not affect later `[IO.File]` calls made with
  relative paths in the same line — they resolve against the process CWD, not the shell's.

## Housekeeping

`ce-probe.py` is kept deliberately: it is the only record of *how* the clang panes were
inspected, and the conclusion in `manual-case-clang.txt` is not reproducible without it.
Scratch `.dxo` containers written for the digest table were deleted after the digests were
read; the digests are in `manual-case-signing.txt`.
