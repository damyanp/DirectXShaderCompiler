# Method notes — issue 4722

Things that cost time or nearly produced a wrong verdict. Written for the next person running
this skill, not for the issue thread.

## 1. The brief's framing was half wrong, and I nearly built the whole case on it

The task described 4722 as a **silent wrong-code** report and warned at length about the
hazards of that shape. That is true of one spelling and false of another: `row_major` written
directly on a template member is a **hard error**, not a silent drop. I discovered this in the
first five minutes of exploration, when the shader I had written from the issue's own test case
refused to compile.

The temptation at that moment is to quietly rewrite `expected.md` so the prediction matches.
I did not; it is left exactly as written and the divergence is §1 of `notes.md`. But the real
lesson is upstream: **the pre-registered symptom should have been written per-spelling rather
than per-issue.** Had `expected.md` enumerated "pragma / explicit qualifier / template argument
/ command-line flag" as four separately-scorable cells from the start, the surprise would have
been a filled-in table rather than a contradiction.

Corollary: when a brief tells you what shape the bug is, that is a hypothesis, not a spec.

## 2. `-verify` scans **comments** for `expected-error`

`dxc -verify` does not restrict its directive scan to the code. A header comment in my copy of
the author's test case that mentioned the literal token `expected-error` — in prose, explaining
what the file was for — was parsed as a directive and produced:

```
cannot find start ('{{') of expected string
```

Fixed by rewording the header comments of `issue-testcase.hlsl` and
`control-verify-nontemplate.hlsl`, **preserving the line count**, because `match-verify.json`
pins `Line 19` / `Line 20`. Re-captured after.

The same hazard applies to `godbolt-note.txt`, which `triage.py godbolt` prepends to the source
and which therefore ends up compiled — and, worse, echoed verbatim into `!dx.source.contents`
in the output pane. Anything you write in that banner is *in the output you are asking the
reader to search*. For this issue that is acute: the note must not contain the literal
`row_major` or `column_major`, or a reader grepping the pane for the orientation gets hits from
my own prose. I wrote the banner structurally — "look at the Buffer Definitions block", "the
compiler default" — and never named the tokens.

## 3. A wrong `--expect` was caught by the tool, not by me

I first ran the `-verify` capture under `match-rejects-qualifier.json` with `--expect match`,
assuming the diagnostic text would be the same. `triage.py` printed:

```
WARNING: control expected match but scored no-repro
```

`-verify` reformats diagnostics — no `error: ` prefix, no source echo — so a predicate written
against normal output cannot score `-verify` output. I wrote a separate `match-verify.json`
and deleted the stale capture. **This is the argument for declaring `--expect` on every run,
including the ones you are sure about**: the declaration is what converts a silent wrong result
into a warning. Two of my three predicates were adjusted because of an `--expect` that failed.

`match-verify.json` is explicitly marked ground-truth-only. Its clauses pin `-verify`'s output
wording and line numbers, neither of which I have any reason to believe is stable across
releases; using it in the history sweep would have manufactured false negatives.

## 4. Presence predicate, and two anti-vacuity controls in opposite directions

The natural predicate here is an absence — "the output does not say `row_major`". It is also
the trap the task warned about: a release that failed to compile emits no `row_major` either,
and scores as a repro for free.

`match.json` is therefore a **presence** predicate (`column_major float4x4 M;`) anchored on
`!dx.entryPoints`, which only exists after successful codegen. But that alone is not enough,
because a predicate can be vacuous in the other direction too — it might be detecting "HLSL
2021 templates compiled" rather than the defect. So there are two controls:

- `control-nontemplate-row-major` (expect **no-match**) — proves the predicate is sensitive to
  the template, not to the cbuffer or the matrix.
- `control-feature-templates` (expect **no-match**) — an HLSL 2021 template with no matrix in
  it, proving the predicate is not just detecting template support.

## 5. The identity control beats any single output reading — but only with its mirror

Comparing `sha256` of the `row_major` and `column_major` builds is stronger than reading one
output, because it needs no knowledge of which layout is "correct" or of how DXC prints it.
Identical bytes from opposite requests is self-evidently a bug.

What it does *not* establish is where the bug lives. `template row == template col` is equally
consistent with "orientation never works in this compiler". The mirror measurement —
`concrete row != concrete col` — is what localises it, and it is not optional. I ran it on
**every release in the sweep**, not just on ground truth, so each row of
`manual-case-release-history.txt` carries its own instrument self-test. A release where the
concrete pair came out identical would have been an instrument failure to investigate, not a
stronger result to report.

Third leg, which I nearly skipped: `template row == template default`. This is what upgrades
"one of the two is ignored" to "the `row_major` one is ignored", and it costs one more compile.

## 6. Measure the default; do not reason about it

HLSL's default orientation and `-Zpr`/`-Zpc` are live confounders. I measured the default on
the build under test (`concrete column_major` and `concrete default` hash identically →
column-major) rather than quoting documentation.

This paid for itself immediately: `-Zpr` turned out to **work** on template-dependent members
while `#pragma pack_matrix` does not. Had I assumed the two mechanisms were interchangeable —
they are documented as equivalent — I would have written "orientation doesn't reach templates",
which is false and would have sent a fixer to the wrong place. The `-Zpr` control is the single
most informative *negative* result on this issue, and it exists only because the default was
treated as something to measure.

## 7. `invalid-probe` needs a positive feature test, not an exit code

Four stable releases predate HLSL 2021 and reject the repro with
`dxc failed : Unknown HLSL version: 2021`. Under an absence predicate they would have scored as
repros; under my presence predicate they score no-match, which would have been read as "fixed
in v1.4.1907" — a fabricated regression window in the wrong direction.

`manual-case-release-history.txt` therefore has a **`2021` column** as the leftmost data
column: does `control-feature-templates.hlsl` compile at all on this release? Rows where it
does not are labelled `INVALID PROBE` and carry no verdict. Don't rely on the tooling to
reclassify these; give every history sweep an explicit feature-presence column and read it
first.

## 8. Corroborate from source before writing the verdict, not after

The measurements alone support "reproduces". Reading the source turned that into a mechanism
that a fixer can act on, and it took about ten minutes: `IsHLSLMatType` →
`getAttr<HLSLMatrixAttr>` → `getCanonicalType()` + `getAs<RecordType>()`, which a dependent
`TemplateSpecializationType` cannot satisfy. Both faces then fall out of the same predicate at
`SemaType.cpp:4359` (skip) and `SemaType.cpp:5820` (reject).

It also produced the best line in the write-up, which is a *comment* in the source
(`SemaType.cpp:4353`) explaining that the pragma and the codegen flag deliberately take
different routes. That is the explanation for the `-Zpr` result I had already measured and
could not otherwise account for. Measurement found the anomaly; source reading named it.

## 9. Compiler Explorer: show the bug, don't merely reproduce it

`repro.hlsl` is built for measurement — it varies one thing at a time, so seeing the defect in
it requires opening two panes and comparing. That is a bad reader experience for an issue
thread.

`godbolt-source.hlsl` is a separate, presentation-only file: both members in one cbuffer under
one pragma, so the two orientations appear on adjacent lines of a single pane. It is compiled
and captured by `triage.py run` like everything else, so it is not an unmeasured claim. Because
it is not `repro.hlsl`, `godbolt --source` requires explicit `id:<args>` for **every** pane.

I also tried an `hlsl_clang_trunk` pane. It compiles the shader cleanly, but emits no matrix
layout annotations at all — so it shows neither the bug nor its absence, and I could not
interpret it in either direction. Dropped, and recorded here rather than shipped; a pane a
reader cannot interpret is worse than one less pane. (Verified by reading the archived
`manual-case-godbolt-verify-17b8ee210e12.txt`, not by assumption.)

## 10. Small mechanical things

- Nonzero exit is not a crash. The rejecting compiles exit `2147500037` = `0x80004005`
  (`E_FAIL`), which is DXC's ordinary "I diagnosed an error" status. No `internal_failure`
  predicate is warranted anywhere on this issue.
- `grep`/ripgrep returns zero matches under `.github/` regardless of content; use
  `Select-String`. This silently made an early search look conclusive.
- Both generator scripts locate `scripts/` relative to `__file__`, `import triage`, and pipe
  all output through `redact_paths()`. `measure_identity.py` also had to use a **relative**
  `-Fo` filename — the echoed command line is part of the captured evidence, so an absolute
  output path would have leaked a machine layout into a file that is supposed to be portable.
- Write captures with `[System.IO.File]::WriteAllText` after normalising CRLF→LF.
  `Tee-Object` and `>` add a BOM and CRLF.
