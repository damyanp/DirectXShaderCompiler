# Method notes: issue 5704

## A multi-line `cmd.txt` pipeline shares output filenames across every release
## in a `bisect`/`run` sweep, and a failed later step silently re-scores an
## earlier release's leftover artifact

`cmd.txt` for this issue is a 3-line pipeline (compile to `lib.bc`, link to
`linked.bc`, `-dumpbin linked.bc`). `execute()`/`_run_command_list()` (the code
path `run`/`bisect` use for an ordinary probe, as opposed to the
`_run_probe_command_list()` isolated-copy path documented for spelling
retries) runs every line with `cwd=<issue dir>` directly, against the *same*
`lib.bc`/`linked.bc` filenames, for every compiler in a sweep. Confirmed by
reading `scripts/triage.py`: `_run_command_list` takes `d` (the issue
directory) as its cwd with no scratch copy and no cleanup between
invocations; only `_run_probe_command_list` (used for the `-pack-optimized`
family of spelling retries) copies to an isolated scratch directory.

dxc's `-link` step only writes its `-Fo` target on a *successful* link. When
one release in a sweep can no longer complete `-link` (as happens here from
v1.8.2403 onward, see `manual-case-release-history.txt`), that release's own
`linked.bc` is never written, and the following `-dumpbin linked.bc` line in
the same 3-line command silently disassembles whatever `linked.bc` an
*earlier, different release* left behind in the shared issue directory. The
disassembly is well-formed and matches the primary predicate, so the sweep
scores that release `repro` -- a real answer to the wrong question.

**Directly measured, not inferred.** `out-v1.6.2106.txt` (link exit 0) and
`out-v1.9.2607.txt` (link exit 1, "Cannot find definition of function main")
were captured in the same bisect sweep at the identical timestamp
(`2026-08-19T22:10:13+00:00`). Both files' `-dumpbin` output carries the
**same** embedded shader hash, `7023918e6966b36ebde405470921951d`, and the
same LLVM identification string `"clang version 3.7 (tags/RELEASE_370/final)"`
-- byte-identical DXIL, despite v1.9.2607's own link having just failed two
lines above it in the same capture. v1.9.2607's `-dumpbin` never ran against
its own output; it ran against v1.6.2106's stale `linked.bc`, which is why the
recorded "always-repro'd v1.6.2106..v1.9.2607" bisect result committed to
`out-v1.6.2106.txt`/`out-v1.9.2607.txt` **is not trustworthy evidence about
any release after whichever one first linked successfully.**

**Left uncorrected, not deleted.** `out-v1.6.2106.txt` and `out-v1.9.2607.txt`
are kept exactly as the tool produced them -- they are the proof this trap
exists, and hand-fixing a capture is exactly the falsification the skill
prohibits. They must not be read as evidence for this issue's release
history; `manual-case-release-history.txt` and
`manual-case-shader-attr-history.txt` (produced by `measure.py` /
`measure-variant.py`, each of which runs every release in its own
freshly-created and freshly-deleted scratch subdirectory, and records a
release as `invalid-probe` whenever its own link step failed to produce
`linked.bc` rather than falling through to `-dumpbin` on whatever is on disk)
are the corrected replacement.

**Generalisation for the skill.** The existing documented hazard ("never
point a release-sweep script at the same output filenames as the
ground-truth run") covers a *sweep script* colliding with a *separate*
ground-truth run. It does not cover the case measured here: a single
tool-native multi-line `cmd.txt`, executed by `bisect` once per release
*inside the same sweep*, whose own intermediate lines collide with each
other release to release. Any issue whose repro is a multi-step pipeline
(compile -> link -> disassemble, or similar) with intermediate `-Fo` targets
is exposed to this, and the failure is invisible in the capture unless the
reader cross-checks the embedded shader hash / IR identification string
across releases, or the earlier step's own exit code, by hand -- the
committed capture header (`# exit:`, `# verdict:`) only reports the *last*
line's exit code, and a compound command whose middle line fails, but whose
last line still runs cleanly against stale prior output, has no exit code
indicating anything went wrong for that release.

Recommendation for `bisect`/`run`, left to collation to evaluate rather than
applied here (no `triage.py` edits from a per-issue session): either (a)
extend the `_run_probe_command_list` isolated-scratch-copy discipline to
every ordinary sweep probe, not only spelling retries, or (b) have the
multi-line runner treat a nonzero exit on any but the final line as
disqualifying the whole probe's output rather than continuing to the next
line regardless.
