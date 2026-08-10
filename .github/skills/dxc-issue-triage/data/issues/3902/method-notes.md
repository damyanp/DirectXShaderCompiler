# Method notes from triaging #3902

Observations about the method and the tooling, not about the issue. Kept out of `comment.md` and
`notes.md` deliberately.

## 1. Diagnostic text is not portable across releases, and `contains` will lie to you

The predicate started as a literal `contains` on `Flags must match usage.` — copied verbatim from
the issue body, which felt like the safe choice. It false-negatived on v1.5.2003, which prints:

```
error: Flags must match usage
```

with **no trailing period**. v1.5.2010 prints `Flags must match usage. Use /Zi for source
location.`; current `main` prints `Flags must match usage.` Three spellings across the range,
same defect.

Two things worth carrying forward:

- Prefer a regex over `contains` for any diagnostic-shaped predicate, and make punctuation and
  trailing hints optional (`Flags must match usage\.?`). Anchor on the invariant part of the
  message and on the numeric note, not on the sentence as printed by one build.
- **The linear bisect alone would not have caught this.** It excludes prereleases, and v1.5.2003
  is a prerelease. The defect only surfaced because the per-release feature matrix ran a wider set
  of tags. A predicate that is silently wrong on the oldest releases produces exactly the shape of
  wrong answer that looks most convincing: a clean "first release that fails", i.e. a fake
  regression window.

Suggested addition to the skill's predicate guidance: when a bisect reports a plausible-looking
first-failing release, re-run the neighbouring older release with a deliberately loosened
predicate before believing it.

## 2. Write controls that are allowed to falsify you

`control-noflags.hlsl` (`RayQuery<RAY_FLAG_NONE>`, unused) was written to confirm that the exotic
`RAY_FLAG_*` template argument in the report was load-bearing. It reproduced, which killed the
hypothesis and produced the sharpest finding in the triage — the trigger is *any* unused
`RayQuery`, and the constant in the diagnostic is a module feature bit, not an encoding of the
template argument.

`triage.py expect --expect ...` handled the correction cleanly, and the falsified prediction is
still in the record, which is the right outcome. The generalisable point: a control whose only
possible result is the one you already expect has not tested anything. At least one control per
issue should be capable of embarrassing the triage.

## 3. Environment hazard: an out-of-band `dxil.dll` next to the ground-truth `dxc.exe`

`build/Debug/bin/dxil.dll` in this workspace is **not** from the ground-truth commit. It reports
FileVersion 1.9.0.5393, branch `damyanp/fix-resource-struct-zero-init`, `dc2088b20-dirty`. `dxc`
prefers an adjacent `dxil.dll` as its external validator, so *any* measurement of a validation
diagnostic taken from that directory is attributable to a binary nobody registered or diffed.

This is not specific to #3902. It silently affects every issue in this workspace whose symptom
comes from the validator, which is a large fraction of the backlog. `probe-internal-validator.py`
in this directory is a reusable pattern: copy `dxc.exe` + `dxcompiler.dll` into a scratch
directory with no `dxil.dll`, forcing the internal validator, and compare. Here the two
configurations agreed exactly, but that had to be measured, not assumed.

Worth considering for the skill's ground-truth verification step: alongside `dxc --version` and
the provenance diff, check whether a `dxil.dll` sits next to the registered exe and, if so, record
its version.

## 4. `--version` is not universally supported

v1.4.1907 and other old releases reject `--version` outright (`dxc failed : Unknown argument:
'--version'`). Anything that identifies a release binary by invoking it needs a fallback;
`measure-release-matrix.py` reads the shipped `dxcompiler.dll` ProductVersion instead.

## 5. Tooling gaps met (all worked around, none blocking)

- `triage.py run --shader ...` retargets **ground truth only**. There is no supported way to run an
  alternative shader against downloaded *releases*, which is what a feature-presence matrix needs
  ("did this release reject my repro for an unrelated reason?"). Hence `measure-release-matrix.py`.
  If this became a first-class flag, the `invalid-probe` classification would get much stronger
  evidence behind it for free. The script reads its clauses out of `match.json` rather than
  duplicating them — worth keeping if it is ever promoted.
- `triage.py labels --issue N` prints `proposed + -` with nothing in it; there is no auto-proposal,
  the reasoning is entirely manual. Not a defect, but the output reads like a tool that tried and
  found nothing.
- The agent's `grep`/ripgrep tool silently returns zero matches for paths under `.github/`.
  `Select-String` and `git grep` both work. A silent zero is the dangerous failure mode: it reads
  as "no such code exists".

## 6. E_FAIL confirmed as a non-signal, again

`0x80004005` / `2147500037` came back for the plain diagnosed validation error here, exactly as the
skill warns. The predicate was written to ignore exit status entirely and key only on message
text. Nothing new, but this issue is a clean worked example if the skill ever wants one: a
`-validator-version 1.7` run of the *same* input exits 0, so exit status alone would have called
that a fix rather than a shim.

## 7. Compiler Explorer: guarded single-source panes

Publishing one source with the interesting code behind `#ifdef USE_RAYQUERY` and giving the third
pane `-DUSE_RAYQUERY` puts the failing and passing cases side by side in a single link, with the
diff between them reduced to one flag that the reader can see in the pane header. Both arms were
verified locally first, and `-Zi -Qembed_debug` (which CE appends) was checked not to change the
outcome before publishing. This seems like a generally reusable arrangement for any issue that has
a known-good variant, and it avoids the "is the second pane even the same code?" question.

Note that `godbolt-note.txt` is compiled into the source, so it must not quote the expected error
text — otherwise the *passing* pane's output contains the error string in a comment and the link
becomes self-contradicting.

## 8. `check_paths.py` is a shared gate, and self-checking it by hand is a trap

Two separate hazards, both met.

**The gate is workspace-wide.** `scripts/check_paths.py` walks the whole skill tree and exits
non-zero for anyone's leak, so during a parallel batch its output is dominated by other workers'
in-flight files and tells you nothing about your own. On my first run it reported 42 findings, all
in `data/issues/4036/` and `data/issues/4168/`; on the final run, 2, in `4036` and the batch-014
orchestrator notes. Zero in 3902 either time. The boundary rules forbid fixing another
directory's files anyway, so the only actionable signal is the subset under your own issue number,
and extracting it requires filtering by hand. An `--issue`-scoped mode (like `audit --issue`)
would make the gate usable mid-batch instead of only at collation.

**My first self-check was a false negative.** I "confirmed" my directory was clean with

```
Select-String -Path *.* -Pattern '<pattern>|<escaped pattern>' -SimpleMatch
```

`-SimpleMatch` disables regex, so the `|` was matched *literally* and the command could never
report a hit no matter what the files contained. It printed nothing, which reads exactly like a
pass. The answer happened to be zero anyway, which is the worst kind of luck: the broken check was
never contradicted.

The reliable move is to run the gate's own matcher over your own subtree rather than reinventing
it — import `check_paths` and call `find_hits()` on the files under `data/issues/<nnnn>/`. Same
regex, same escaped-separator handling, same definition of a hit, scoped to what you own. Any
hand-rolled grep is a second implementation of the rule that can disagree with the gate silently.

Related: generators should redact at emit time, not after the fact. `measure-release-matrix.py`
and `probe-internal-validator.py` both funnel every path through a `display()` helper before it
reaches the file, so regenerating them cannot reintroduce a leak, and nobody has to hand-edit
generated evidence to satisfy the gate. Post-hoc redaction of generated output breaks the
guarantee that re-running the script reproduces what is on disk.

## 9. Cross-issue observations (deliberately not in the draft)

While calibrating the `validation` label against its existing users I noticed two open issues that
look like they may live in the same area — one about `RayQuery` producing corrupted DXIL, and one
about DXC setting a shader flag the validator then disagrees with. I have not verified any
relationship, it is out of scope for a single-issue triage, and the draft comment says nothing
about it. Recording it here only so a human can decide whether the area deserves a grouped look.

The issue's own timeline has **no** cross-referenced events at all — no linked PRs, no duplicate
links, in four and a half years.
