# Method notes from #4206

Observations that should change how future batches run. Nothing here is a claim about #4206
itself; that is in `notes.md`.

## 1. A release tag's tree is not a proxy for that release's shipped binary

This one cost real time and would have produced a wrong attribution if trusted.

`git merge-base --is-ancestor 4234a9ae5 v1.4.1907` **succeeds**, and
`git show v1.4.1907:lib/HLSL/DxilCondenseResources.cpp` contains `MarkCBUse` and
`UpdateCBufferUsage`. From source alone one would conclude v1.4.1907 has the CB-usage
metadata mechanism. The shipped v1.4.1907 binary demonstrably behaves as though it does not.

The explanation is visible in the dates: `4234a9ae5` is 2019-08-12, the `v1.4.1907` tag tip is
2019-08-30, and "1907" means the July 2019 release. The tag was placed on a branch tip that
kept moving after the artifacts were built.

**Rule to apply:** when a release binary and the release tag's source disagree, the binary
wins, and no commit should be named. `git merge-base --is-ancestor <sha> <tag>` is sound for
proving a commit is *outside* an older tag, but proving it is *inside* a tag says nothing
about whether it is inside that release's **download**. SKILL.md's attribution guidance
(count commits in the window, state the window size, call it strong rather than certain) is
right, but it should probably add: check the tag tip's date against the release date before
citing the tag at all.

## 2. Pre-registering the positive control is what caught the second bug

`expected.md` named `WorldPosToProbeCoord` as the presence control — "it is genuinely used, so
it must show `D3D_SVF_USED`; if it does not, the instrument is broken". The very first probe
showed it as `0`.

The tempting reading was "instrument broken, try something else". The correct reading was that
the control had found a second, unreported face of the same defect, which a third variable
(`ProbeCoordToWorldPos`, also genuinely used, reported correctly) immediately distinguished
from instrument failure.

**Generalisation:** a failing positive control is ambiguous between "the instrument is broken"
and "the defect is bigger than reported". Resolving it needs a *second* positive control that
exercises the instrument without exercising the suspected defect. Pick presence controls in
pairs where the surface allows it. `expected.md` earns its keep here precisely because it was
wrong on the record.

## 3. The "reflection metadata relocated between parts" trap has a cheap discriminator

Batch 013 recorded a v1.4.1907 → v1.5.2010 transition that was an artefact: reflection
metadata moved from the DXIL part into `STAT`, so a text predicate over disassembly stopped
matching. This issue has a genuine transition at the same boundary, and distinguishing them
took three cheap things, all worth making routine for reflection issues:

1. **A fixed-reader column.** Vary only the compiler; hold the reflection reader at ground
   truth. A difference then has to come from the container. Add a matched-pair column for
   real-world relevance, and report that the two agree (or where they do not).
2. **A per-release self-test clause inside the predicate**, not as a side note — here, a third
   variable that must be reported used. It fires automatically on every row, so an
   unmeasurable row cannot silently score as "fixed".
3. **A per-release negative control shader.** `control-noneg.hlsl` scoring fully correct on
   v1.4.1907 proves that release's reader could tell used from unused at all.

With all three, "the data merely moved" is excluded without any archaeology.

## 4. Record a prediction for every control run, including ones you expect to confirm

The `-validator-version 1.4` probe was run with `--expect no-match` and came back `repro`. The
mismatch warning is now in the capture, and the write-up says the simple mechanism story was
tested and refuted rather than quietly presenting a mechanism that had not been checked.

Had `--expect` been omitted, the same result would have been easy to rationalise away. The
`--expect` flag is worth using on *hypothesis* probes, not just on controls whose answer is
already known.

## 5. Tool friction encountered (no changes made)

- **`ground_truth_compiler()`** (`triage.py:1678`) returns `None` once more than one
  `out-<id>.txt` exists in an issue directory, so `--compiler <id>` has to be repeated on
  every `run`. Easy to forget; the failure is a confusing error rather than a wrong result,
  so it is low-severity, but a hint in the error text naming the candidates would help.
- **`triage.py compiler --commit`** warns when the SHA is absent from the version string. For
  a harness-as-compiler that is expected and benign — the harness's "version" is its own
  description. Worth a sentence in SKILL.md so nobody treats the warning as a provenance
  failure.
- **`dxa` has no `--version`**, and its error text prints an absolute path. Identifying the
  reader by `sha256(dxcompiler.dll)` beside it works and keeps absolute paths out of
  committed artifacts. Recommended for any future `dxa`-based harness.
- **`dxa` positional parsing** needs the `-o=...` / `-extractpart=...` forms quoted in
  PowerShell, otherwise it fails with "Too many positional arguments".
- **`grep` under a dotted directory** silently returns zero matches, as SKILL.md warns.
  `Select-String` and `git grep` were used throughout.
- **`check_paths.py` skips any file containing a NUL byte** (`committable_text_files()` does
  `if b"\0" in data: continue`, to avoid binaries). A UTF-16-encoded artifact is full of NULs
  and would therefore pass the gate without ever being scanned. Measured rather than assumed:
  under this shell (PowerShell 7.4.18) `>` redirection writes UTF-8 with no NUL bytes, so the
  trap does not bite here — but Windows PowerShell 5.1 defaults `>` to UTF-16LE, so a worker
  on the older shell could redirect a capture to disk and have it silently exempted. Writing
  artifacts through Python with `encoding="utf-8"`, as the harness and matrix here do, avoids
  it. Worth either widening the gate's skip test to a real binary sniff, or having workers
  assert their artifacts are UTF-8.

## 6. Reusing the tool's own predicate evaluator in a manual matrix

`measure-history.py` calls `triage.predicate_clause_signature()` and `triage.classify()`
rather than re-implementing the match. The matrix therefore cannot drift from the JSON
predicates, and per-clause booleans are available for free — which is what makes the
instrument self-test checkable on every row. Recommended as the default shape for any
`manual-case-*` history where `bisect` cannot be used.
