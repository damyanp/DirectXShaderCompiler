# Method notes — from triaging 4615

Observations about the *method*, not about the issue. Issue-specific findings are in `notes.md`.

## 1. The general shape for a debug-metadata issue: presence-anchored predicate + a per-release self-test table

The brief warned that absence-based predicates are satisfied by failure. The concrete pattern that
worked, and that should generalise to any "the compiler emits the wrong X in metadata" issue:

- **Put the wrong value in as a `regex`, not the right value as a `not_regex`.** Here, "line 9
  survives" is the symptom stated positively; the two `not_regex` clauses for `line: 400` and the
  virtual `!DIFile` are corroboration, not the load-bearing part.
- **Add a clause that is true under both behaviours** and would only fail if the instrument broke.
  A statement placed *before* the `#line` directive reports line 7 either way, so
  `!DILocation\(line: 7,` is a self-test that costs one clause and converts every mode of
  metadata-loss into `no-repro` instead of a false `repro`.
- **Score the self-test per release, in the same capture the predicate scored, and print it as a
  table.** `release-matrix.py` re-reads each `out-v*.txt` and emits verdict / selftest /
  `!DILocation` lines / `!DIFile` names. That single table answers three questions at once —
  was debug info present, did the node spelling drift, and what did each release actually print —
  and it is the artifact a reviewer can check in ten seconds. Recomputing from stored captures
  costs nothing and needs no reruns.

Worth noting: `_has_positive_clause()` already warns about unanchored absence predicates, and it
was satisfied here by the two presence clauses. That warning is a floor, not a ceiling — it would
also have been satisfied by two presence clauses that could not detect instrument failure. The
self-test has to be *chosen* to be invariant under the behaviour change; the tool cannot check that
for you.

## 2. Falsify the absence clause on the ground-truth build, not just on an old release

`v1.4.1907` emits `line: 400`, which proves the absence clauses *can* fail. But that is a 2019
binary, so it also leaves open "maybe only old builds can print that". `control-physical400.hlsl`
— 401 physical lines, `return` genuinely on line 400, no `#line` at all — makes `main` itself
print `!DILocation(line: 400,` and scores `no-match`. Cheap, and it closes the gap that the
historical control leaves open. General rule: **an absence clause should be shown falsifiable on
the build you are making the claim about.**

## 3. `-Zi` is what produces the metadata; `-Qembed_debug` is not

For a stdout-disassembly predicate, `-Zi` alone is sufficient and `-Qembed_debug` changes the
output not at all — byte-identical stdout hash. `-Qembed_debug` only silences a warning and
affects the container. Easy to assume the pair is load-bearing and then be unable to say which
half mattered. Measure per flag; the hash column makes it a one-line answer.

## 4. The dxc flag-provenance asymmetry, measured

`/ZZZNONSENSE` exits **0** with byte-identical output. `-Qembed_debugZZZ` exits **1** with
`Unknown argument`. So the `-` spelling *does* reject unknown flags and the `/` spelling does not.
This is useful beyond the warning in the brief: **to prove a flag was parsed, it is enough to
misspell it with a leading `-`.** Pointing a flag at a missing path (`-Fd no-such-directory\`)
also works and is the only option for flags whose spelling you cannot corrupt. A capture that
records all of exit code, stdout hash, and stderr for each flag variant costs one small script and
settles the whole question.

## 5. Compiler Explorer shifts every line number — a specific trap for line-number issues

CE prepends a banner to the source, so physical line numbers in the pane do not match local
output: the shift was **+20** in a 3-pane pixel-shader link and **+24** in the 4-pane compute link
built from the same shader. For most issues this is invisible. For a `#line` / line-number /
`__LINE__` issue it is directly on top of the claim being made — a reader comparing the comment's
`line: 9` against CE's `line: 33` could reasonably conclude the evidence does not replicate.
**When the symptom is a line number, state the shift in the comment and in `godbolt-note.txt`.**
The shift depends on the pane layout, so re-measure it after any republish.

## 6. Republishing to CE archives the previous verify file

`godbolt --source` wrote `manual-case-godbolt-verify.txt` for the new link and moved the old one
to `manual-case-godbolt-verify-<id>.txt`. Good behaviour, but it means the directory ends up with
a verify file for a link that must not be cited. Both `notes.md` and `godbolt-note.txt` now name
the superseded link explicitly as superseded; without that, the archived file is indistinguishable
from current evidence to anyone reading the directory later.

## 7. Read the CE panes from the verify file, not the console summary

The console summary truncates. `manual-case-godbolt-verify.txt` holds all four panes in full, and
the Clang-vs-DXC contrast was only visible by reading it. Also: the CE API returns an empty body
unless `Accept: application/json` is sent, and CE's *default* output filters strip the metadata
block entirely — `triage.CE_FILTERS` (notably `commentOnly: False`) has to be reused or the panes
come back with no `!DILocation` at all. That failure looks exactly like "the compiler emitted no
debug info", which on this issue is the very thing being ruled out.

## 8. When comparing against `hlsl_clang_trunk`, run `dxc_trunk` on the identical source in the same capture

The Clang front end honoured `#line` here. That is only interesting if the shader is known to be
the same one DXC fails on — CE panes are edited independently and a restating can drift. Pairing
the two compilers on one source in one capture, with the DXC pane as the control, makes the
comparison self-evidencing. It also caught that this is not stage-specific: the compute restating
behaves like the pixel original.

## 9. The linear bisect says "non-monotonic" for a single transition

`bisect --linear` printed "non-monotonic history … transitions at v1.5.2010 -> repro" on a history
with exactly one transition. It is the scan's phrasing for *any* transition list, not a signal of
a second window. Mildly alarming on first read; worth not chasing.

## 10. `triage.py sql` column names

`compilers` has `exe_path` and `git_commit`, not `exe` and `commit_sha`. Costs a round trip every
time.

## 11. A resolved thread still needs measurement, and the measurement was not redundant

The thread was already answered by a maintainer in 2022 and the reporter had accepted the default.
It would have been reasonable to record "intentional, closed by discussion" without running
anything. Running it produced three things the thread does not contain: the boundary is
**v1.5.2010**, not the "validator >= 1.6" in the report; `-ignore-line-directives` exists and moves
in the opposite direction, so a reader searching for the requested flag will find a
similar-sounding one that makes things worse; and the Clang-based front end already behaves the
way the reporter asked for. **A thread being resolved is not a reason to skip the measurement —
it changes what the measurement is for, from "does it repro" to "is the recorded explanation still
accurate and complete".**

## 12. For collation: a successor issue exists

#8679 (2026-07-27) re-raises the same request, cites #4615, and is labelled `bug` +
`needs-triage`. Per the method, `comment.md` says nothing about it. But the pair wants a single
decision, not two, and the direction matters: **#4615 is the original, #8679 the successor.**
Finding E in `notes.md` (Clang already honours `#line`) bears directly on #8679's second ask. If
collation only reads verdict rows it will miss this; the relationship is recorded in `notes.md`
§10 as well as here.

## 13. `text_stale` was considered and deliberately not set

The report says "validator version >= 1.6"; the measured boundary is v1.5.2010. That is an
inaccuracy in the *original* filing, not drift in the compiler since — the behavioural description
is exactly right today. Setting `text_stale` for it would misdirect a reader into thinking the
description no longer matches the compiler. The distinction worth keeping: **`text_stale` is about
the world moving under the text, not about the text having been imprecise when written.** The
correction still belongs in the comment; it just is not staleness.
