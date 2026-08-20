# Method notes — #5040

Observations about the *method* (not the verdict), for collation to review and possibly
promote into `SKILL.md` / `triage.py`. This issue's worker does not edit shared files.

## `dxc -dumpbin <file>` prints disassembly straight to stdout, no `-Fc` file needed

`-Fc <file>` writes disassembly to a file, which the runner's stdout/stderr capture cannot
see (SKILL.md already documents this for `-P`). For a mode whose result has to be brought back
into a scored capture, `-dumpbin` is a second, cheaper route than a `-Zi` reflow trick: compile
once with `-Fo <container>`, then a second `dxc -dumpbin <container>` invocation prints full
disassembly to stdout with no extra flags and no output redirection. Both invocations belong on
separate lines of `cmd.txt`; the runner already concatenates multi-line `cmd.txt` output, so
this composes for free. Might be worth adding next to the existing `-P`/`-Zi` note in step 4.

## A produced binary artifact (`-Fo` container) should not be left committed

Using `-Fo out.dxil` in `cmd.txt` causes `run`'s `sync_outputs` step to copy the produced
`.dxil` container back into the issue directory after every probe. Checked precedent across
existing issue directories (`4958`'s `-Fo output.dxil`, `3005`'s `-Fo pdb/a.dxbc`): none commit
the produced binary itself, only a `.gitignore`'d placeholder directory when the tool needs a
directory that doesn't otherwise exist (`3005/pdb/.gitignore`, matching the `dbgdir/` pattern
already documented in `SKILL.md`). Deleted `out.dxil` from this issue's directory by hand after
capturing its disassembly via `-dumpbin`, since the disassembly text (not the binary) is what
`out-main-debug.txt` / release captures / `reindex` actually need. Worth stating explicitly in
`SKILL.md` next to the existing `dbgdir/` guidance: a bare produced container in the issue root
(not inside a gitignored subdirectory) is noise to remove before committing, not evidence to
keep.

## `main-debug.json`'s free-text `provenance_note` field was stale, but harmless

`.cache/compilers/main-debug.json` carried a `provenance_note` naming a different self-reported
SHA and a different claimed-upstream-equivalent commit than the build this batch actually
registered (`git_commit` field, which *is* correct and matches the batch brief exactly).
`grep -n provenance_note scripts/triage.py` (well, `Select-String`, since ripgrep silently skips
dot-directories under `.github/` — SKILL.md already warns about this and it is worth
re-confirming here: the plain `grep` tool in this session returned "no matches" for the same
query, silently) returns no hits, so the field is not read by any command; it must be leftover
free text a previous session added by hand for its own documentation and never updated on a
later rebuild. Did not edit `.cache/` (shared, machine-local, and out of this issue's write
scope); recording it here so collation can decide whether to refresh it once, since a stale
provenance note sitting next to a correct `git_commit` is exactly the kind of thing a future
worker could misread as a discrepancy worth investigating (as this one briefly did).

## `check_paths.py` currently fails on other issues in this batch, not on #5040

Ran `python scripts/check_paths.py` as a spot check; it reports unredacted machine-local
absolute paths in `data/issues/5079/...` and `data/issues/5080/...` (other issues, presumably
from concurrent batch-019 workers). Filtered output confirms zero hits under
`data/issues/5040/`. Not investigated or touched further — those are other issues' directories,
and collation is where a batch-wide `check_paths.py` failure belongs.
