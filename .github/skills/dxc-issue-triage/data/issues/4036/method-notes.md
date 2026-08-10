# Method notes from #4036

Observations about the *method*, not about the issue. Written for whoever runs
the next batch.

## 1. A flag quoted in the issue title can silently shorten the history

The original title of #4036 was `[hlsl 2021] Odd compiliation error`, so the
first `cmd.txt` carried `-HV 2021`. Four old releases (v1.4.1907, v1.5.2010,
v1.6.2104, v1.6.2106) answer

    dxc failed : Unknown HLSL version: 2021

and exit 1. The runner classifies that as `invalid-probe`, correctly and for
the right stated reason — but the reason has nothing to do with the issue. The
reported range therefore began at v1.6.2112, and it *looked* like the natural
consequence of `ResourceDescriptorHeap` being a Shader Model 6.6 feature.

It was not. Dropping the flag showed that v1.6.2104 (2021-04-20) and v1.6.2106
both fully support `ps_6_6` and `ResourceDescriptorHeap`, and both reproduce
the filed diagnostic — six months *before* the issue was filed. The real
Shader Model 6.6 floor is v1.6.2104; only v1.4.1907 and v1.5.2010 genuinely
predate the feature.

Two probes are needed to tell these apart, and neither is the repro:

- a feature-presence control (`control-heap.hlsl`) that uses the feature and
  nothing else — if it fails too, the release really is too old;
- an equivalence control: run every case with and without the flag on every
  release and diff. Here 51 comparisons were byte-identical and 12 differed,
  the 12 being exactly the 4 releases that reject the flag × 3 cases. That
  makes "the flag is inert" a measurement rather than an assumption, and it is
  what justified removing it.

Generalisation: **an argument that came from the issue's prose is a hypothesis,
not a given.** If it is not needed to produce the symptom, it can only cost
history. Test it before it silently truncates the range. `cmd-as-filed.txt`
keeps the reporter's exact configuration so nothing is lost.

The `SELF-TEST` line in `release-matrix.py` exists for this: a matrix that
reports "all identical" is worthless unless it can also report a difference.
It prints both totals and fails if only one outcome ever occurs.

## 2. `_predicate_quotes` protects one predicate, not the issue

The #3055 trap — a valid diagnostic being demoted to `invalid-probe` because it
happens to contain a feature-absence marker like `no member named` — is
suppressed when the predicate itself quotes that marker verbatim in a positive
clause. That works for the primary predicate.

It does not work for a *second* predicate. This issue needed
`match-crash.json`, an `internal_failure` predicate, to measure the newer half
of the history. An `internal_failure` predicate has no `contains` clause, so it
quotes nothing, so the suppression cannot fire — and v1.6.2112's perfectly
valid diagnostic was demoted to `invalid-probe`. That silently deleted the one
release that proves the internal error is a regression rather than the original
behaviour.

The symptom is nasty because the deletion looks like a correct exclusion: the
release "didn't have the feature", says the label, on a release that plainly
did.

Mitigation used here: a third, composite predicate
(`match-fails.json` = `any_of[contains(<the diagnostic>), internal_failure]`)
whose `contains` clause quotes the marker, so suppression fires and the whole
history is measurable in one pass. That predicate is the one the verdict's
history is built from; the two narrow predicates locate the boundary inside it.

Generalisation: **when a symptom changes shape across the history, add the
union predicate and bisect on that**, then use the narrow predicates only to
find where one shape becomes the other. Also: whenever a probe is demoted,
check the demotion against a feature-presence control before believing it.

A possible tooling change: `_predicate_quotes` could consider every predicate
recorded for the issue rather than only the one being scored, or `classify`
could refuse to demote a probe whose exit code is the ordinary diagnosed-error
code (`0x80004005`) when a sibling predicate quotes the marker.

## 3. `cdb` from Python: do *not* route through `cmd.exe`

The method document warns against invoking `cdb` from PowerShell, because
PowerShell re-quotes arguments. The natural over-correction is to wrap the call
in `cmd /c` from Python too. That breaks:

    '"C:\Program Files (x86)\...\cdb.exe"' is not recognized as an internal or
    external command

`cmd` mangles a command line that both begins with a quote and contains further
quotes. Passing the argument vector straight to `subprocess.run` with no shell
works exactly as intended. The warning is about PowerShell specifically, not
about needing `cmd`.

## 4. `cdb` interleaves warnings *inside* a stack

`capture-stack.py` originally stopped collecting frames at the first line that
did not look like a frame. `cdb` emits

    *** WARNING: Unable to verify checksum for ...

*between* frames, so the capture was truncated to a single frame — and a
one-frame stack still looks superficially plausible. The harness now skips
`***` and blank lines while inside a stack, and prints a `PARSE-WARNING`
self-test line when it expected frames and found none. That warning fired on
the broken version, which is the only reason the truncation was noticed.

Generalisation: **a trimming harness needs a self-test that fails loudly on an
implausibly small result.** Silent truncation is the failure mode.

## 5. A `git grep` that finds nothing is a claim, and PowerShell can fake it

Searching the test tree with

    Get-ChildItem -Path tools\clang\test -Recurse -File -Include *.hlsl

returns nothing, because `-Include` is ignored unless the *path* ends in a
wildcard. The conclusion drawn from it — "no test covers this construct" —
was written into an evidence file before `git grep` found three tests that do.

The tests turned out not to change the verdict (all three are `-ast-dump` or
`-verify` and stop before code generation, which is exactly why they did not
catch the crash), but that was luck. Use `git grep` for repository content;
it takes pathspecs directly and cannot be silently disabled by a quoting rule.

Generalisation: **prove a negative search can produce a positive.** The same
discipline the matrix self-test applies to comparisons applies to searches.

## 6. A generator that prints its own repo root leaks a machine path

`source-window.py` computed the repository root from `__file__` — which is
correct, machine-independent logic — and then printed it into the header of
`manual-case-source-window.txt` as a provenance line. The logic was portable;
the *output* was not, and it is the output that gets committed.
`scripts/check_paths.py` caught it.

The fix belongs in the generator, not in the generated file: the header now
says the commands run with the repository root as their working directory and
that all pathspecs are repository-relative, and the file was regenerated. Hand-
editing the output would have satisfied the gate while breaking the promise
that re-running the script reproduces what is on disk.

Generalisation: **a script may know an absolute path; it may not print one.**
When a generator wants to record provenance, record the property (repo-relative
pathspecs, `<repo>`-rooted executable) rather than the literal location. Run
`python scripts/check_paths.py` after generating any `manual-case-*.txt`, not
only at the end of the triage — it is cheap and it points at the line.

Nothing in this issue's directory needs an `ALLOWLIST` entry. The one absolute
path that remains in evidence is the Windows SDK install location of `cdb.exe`
inside the captured command line in `manual-case-cast-stack.txt`; it is a
standard product path, not a checkout or user-profile path, and the gate does
not reject it.
