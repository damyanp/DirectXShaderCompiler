# Method notes from #4307

Observations about the *skill*, not about the issue. Kept separate so the write-up stays about
DXC.

## 1. `godbolt-note.txt` is prepended to the source, and that can destroy the evidence

`triage.py godbolt` puts the note above the shader, so every line number in the CE output is
shifted by the size of the note plus the generated banner. Here the note was 6 lines, the banner
made it 9, and the repro's line 11 appeared as `<source>:20`.

For most issues that is cosmetic. For **this** issue the line number *is* the symptom — the whole
report is "it says line 11, it should say line 22" — so a reader following the CE link sees
neither number and has no way to know why. I wrote the note to describe the relationship
structurally ("11 lines further down") rather than quote absolute numbers, but that is a
workaround.

Worth considering for the skill: either warn that the note shifts line numbers whenever the
symptom is a location, or emit the note as a trailing comment block for those issues.

## 2. An `invalid-probe` on ground truth can be the finding, not a setback

Step 5 treats `invalid-probe` as "the probe never reached the code under test", and the reflex is
to fix the probe. Here the ground-truth Debug build exited `0x80000003` because it **asserts**
before reaching the reported symptom — so the classification was right and the *cause* was the
interesting part.

What worked: keep the original predicate, add a second one (`internal_failure`) so the assert is
scored rather than narrated, and capture the release path separately by continuing past the trap
in cdb (`g;gh;g;q` — `gh` is "go with exception handled", which is what a NDEBUG build does with
the assert compiled out). That yields two captures, one per build configuration, and neither
claim rests on prose.

Might be worth naming in the skill: *when ground truth scores `invalid-probe`, ask whether the
Debug build is telling you something before assuming the harness is wrong.*

## 3. Searching `tools/clang/test/` first reframed the entire verdict

The skill's advice to corroborate from source is stated as strengthening a finding. Here it
*changed* it. Grepping the test suite for the phenomenon (rather than the code for the message)
found `shader_targets/mesh/readFromOutIndices.hlsl`, which expects a clear, located diagnostic
for the neighbouring expression shape.

Without that, the honest verdict would have been "reproduces; enhancement; someone should write a
diagnostic". With it, the verdict is "the diagnostic exists and is guarded by
`isa<ArraySubscriptExpr>`" — a one-file change with a test already in the tree. Same evidence
budget, far more actionable.

Suggested addition to step 4 or 11: for a *diagnostic-quality* issue, search the test suite for
the good diagnostic before concluding one does not exist. The absence of a message in your
capture is not the absence of the check.

## 4. `str.replace` makes silent no-ops, and variant generators are exactly where that bites

`make-variants.py` derives every control from `repro.hlsl` by replacement. One anchor
(`[ numthreads( 64, 1, 1 ) ]`) did not exist in the file — the real text was
`[numthreads(128, 1, 1)]` — so the replacement did nothing, and the generator cheerfully wrote a
"variant" that called an undeclared function. It would have compiled with an error, the error
would have been about the harness, and nothing in the pipeline would have said so.

Fixed by routing every variant through a `derive(*pairs)` helper that `sys.exit`s if an anchor is
absent, plus a check that the result differs from the repro. This is the same class of bug the
skill already warns about for transcribed command lines: **a string operation that quietly does
nothing looks identical to one that worked.** The line-count assertion that was already there did
not catch it, because the bogus variant had the right number of lines.

## 5. A matrix that proves an absence needs a second self-test

The skill's control discipline gave `release-matrix.py` a self-test: the control must compile
cleanly somewhere, or the harness is measuring nothing. That covers "everything fails".

But the central claim here is an **absence** — "no source-level diagnostic is emitted for the
repro" — and an absence is only as good as the instrument. So the matrix carries a second
self-test: the positive case (`elem-read`) must emit the good diagnostic on at least one release.
Both report a count (18/20 each), so a reader sees the instrument working rather than taking my
word for it.

Generalisable: *whenever the finding is "X does not happen", add a control where X does happen,
and assert it in the harness.*

## 6. Test every reading of an ambiguous sentence before calling the text stale

The body's last sentence could mean "the member is the argument" or "the element is the
argument". The first compiles cleanly; the second produces the *good* diagnostic. Neither
produces the reported error, which is what makes `--text-stale` defensible — but had I tested only
the first, I would have recorded a staleness claim resting on one arbitrary reading of an
ambiguous sentence, about a five-year-old report, in a way that reads as diagnosing the reporter.

The extra variant cost one run. The skill's bar for `--text-stale` is high; enumerating the
readings is a cheap way to meet it.

## 7. Small mechanical things

- From `data/issues/<nnnn>/`, the repo root is `Path(__file__).resolve().parents[5]`. I got
  `parents[4]` (`.github`) first and it produced a capture whose only content was "cannot find the
  file". Both scripts now `assert REPO.name == "DirectXShaderCompiler"` and check the exe exists,
  so a wrong path fails at line 1 instead of producing a plausible-looking empty capture. This is
  the "a negative result from a command that errored is not a negative result" trap in miniature.
- The agent `grep`/ripgrep tool silently returns zero matches under `.github/` (ignore rules).
  `Select-String` works. Anything searching the skill's own directory needs it.
- `triage.py sql "... exe ..."` fails: the column is `exe_path`, and `cached_path` can be NULL —
  use `CASE WHEN cached_path IS NULL THEN 0 ELSE 1 END`. In PowerShell, pipe `sql` output through
  `ConvertFrom-Json | Format-Table`; piping it into `python -c` does not work.
- `triage.py expect --issue N --capture <file> --expect <value>` is the sanctioned way to revise a
  declared expectation, and it refuses a declaration the capture contradicts. Used once here,
  after `case-out-param` falsified my `invalid-probe` prediction.

## 8. The batch name was not in the brief

`fetch` needs `--batch` and the assignment did not name one. I used `batch-012` for the fetch,
which is wrong — it already holds 8 issues — and set `batch-015` on the verdict, inferred from
`batch-014` being the highest existing batch and from 4341/4351/4384 being worked concurrently.
The `runs` row for the fetch still carries the wrong name. Worth either defaulting `--batch` to
"next unused" or having the brief template require it.

## 9. Cross-issue observation (kept out of the draft, per the brief)

The draft says nothing about other issues. For the record: #4307's mechanism —
`LegalizeDxilInputOutputs` having no case for a qualifier and falling through its `bLoad &&
bStore` switch — is a general shape, and the `DXASSERT(0, "invalid input qual here")` at
`ScalarReplAggregatesHLSL.cpp:6065` predates mesh shaders (`deb9f3fd2`, 2017-01-25). Any other
issue in the backlog whose Debug repro lands on that assert is likely the same root cause with a
different qualifier. I did not search for one; that is a batch-level question.
