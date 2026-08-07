# Method observations from #2128 — for collation to promote or discard

Recorded here rather than edited into `SKILL.md` / `triage.py`, per the single-writer rule.

## 1. The predicate vocabulary cannot express a symptom that is a *quantity*

`match.json` sees exit codes and output text. #2128's symptom is a byte ratio, so there is no
predicate, the issue is `unscored`, and `bisect` is inapplicable — its short-circuit on
agreeing endpoints would have reported nothing at all.

The workaround that worked: put the falsifiable rule in `expected.md`, evaluate it with a
committed script (`measure.py`), and capture the output as `manual-case-*.txt`. That is the
#2427/#3150 precedent (`classify()`'s docstring already anticipates it) applied to a
measurement rather than to a command line.

**Possible promotion:** SKILL.md's step 4 assumes a predicate always exists. A paragraph saying
"when the symptom is a quantity, the predicate is a committed script and the issue is
`unscored`" would save the next worker the derivation. Cheaper than adding a `size`/`ratio`
predicate kind, which would need a baseline the framework has nowhere to store.

## 2. `bisect` has no analogue for a quantity, but the history search is still cheap

All 20 releases were already cached, so `measure.py --history` compiled a 3-shader corpus with
every one of them in about a minute and produced a full ratio-vs-date table. **A quantity
history is a linear scan by construction** — there is no monotonic predicate to bisect on — but
that is affordable and it is what showed the ratio has not moved since v1.4.1907 while raw size
dropped 39%. An issue that looks unbisectable may still have a fully measurable history.

## 3. A ratio predicate can key on a denominator that changes under you — mine did

`expected.md` committed to "dxc whole-container deflate ratio ≥ 0.70". Measured 0.613 by
default and 0.771 with `-Qstrip_reflect`. The rule was not wrong about the defect; it was wrong
about the *quantity*, because DXC started emitting a `STAT` part (a clone of the module) after
the report, and deflate deduplicates it against `DXIL`. The container ratio therefore improved
while the zipped byte count for a small shader got **worse** (2106 → 2393 B).

**Generalisable rule:** when the symptom is a ratio, pre-commit on a quantity whose definition
cannot change — zipped bytes for a fixed corpus — not on a ratio whose denominator is compiler
output. I kept the original rule visible and explained the override rather than restating it,
which is the behaviour SKILL.md wants, but the trap is worth naming.

## 4. An agent-constructed corpus can bias the very number under test

`corpus-large.hlsl` uses `[unroll]` 32×, so its object is 32 near-identical blocks. That
flatters *both* compilers (fxc reaches 0.059) and dragged the corpus total from 0.613 to 0.529.
Nothing in the framework would have caught it. It was caught by reading the per-shader rows,
and the fix was to emit an explicit "TOTAL excl. unrolled" row so the bias is visible in the
capture instead of being argued for in prose. **A constructed corpus for a size/perf issue
needs at least one deliberately unrepresentative member and an explicit subtotal without it.**

## 5. Control discipline transfers cleanly from predicates to measurements

SKILL.md's "give every text-based predicate a control" generalised without modification: two
byte-stream controls (incompressible sha256 chain ≥ 0.98, compressible source text ≤ 0.50) pin
both ends of the scale, and `measure.py` re-runs them on every invocation and refuses to print
compiler numbers if either fails. Worth stating in SKILL.md that the rule is about *any*
instrument, not only `match.json`.

## 6. Tooling defect: `run --shader X` and an `-Fo` in `cmd.txt` are incompatible

`retarget_cmd` replaces only the source operand, so an `-Fo out.cso` in `cmd.txt` would make
every corpus shader write the same output file and silently overwrite the previous one. Worked
around by keeping `-Fo` out of `cmd.txt` and giving `measure.py` its own invocations. A warning
in `retarget_cmd` when the line contains `-Fo`/`/Fo` and `--shader` is in use would close it.

## 7. A size-issue corpus produces a large committed capture, and it must not be trimmed

`variant-large-main-debug.txt` is 291 KB — the full disassembly of a 32×-unrolled shader. A
size/perf issue needs a big shader; captures are committed verbatim and hand-editing one is
falsification (SKILL.md: "`# exit:` and the output below it are observations"). So the two
requirements pull against each other and the honest resolution is to keep it. The only clean
alternative would be an `-Fo` in `cmd.txt` to suppress disassembly, which `run --shader`
cannot support (see item 6). Worth a sentence in SKILL.md so the next worker does not "tidy"
one.

## 8. Minor: release exe layout differs between v1.4.1907 and everything after

`v1.4.1907`'s cached `dxc.exe` is at the archive root; every later release is at
`bin/x64/dxc.exe`. A hand-written path guessed from the newer layout fails with a bare
`FileNotFoundError` from `subprocess`. `resolve_compiler`/`ensure_release` handle this
correctly via `find_dxc`; anything driving the release binaries directly must read
`releases.cached_path` rather than construct a path. Cost me one wasted run.

## 9. Cross-issue observation (deliberately kept out of `comment.md`)

No cross-reference exists in #2128's timeline (23 events: labels, project moves, mentions — no
`cross-referenced`, no linked PR, no milestone-carrying commit). So there is no lapsed
resolution to check, unlike #2427. If collation finds another open issue about container or
cache size, this measurement transfers to it directly; the draft says nothing about any other
issue.

## 10. `godbolt --skip` was the right call, and it took work to be sure

SKILL.md warns that #1627's skip was reconsidered once a Clang pane was tried. I checked:
Clang's HLSL path emits the same LLVM bitcode encoding, so it *inherits* the property rather
than contradicting it — but a CE pane shows text disassembly and cannot display a byte count or
run deflate, so the pane would assert the finding rather than show it. **The reusable
distinction: a Clang pane rescues a skip when the question is "does the successor compiler
agree?", and cannot rescue one when the quantity under test is not renderable as text.**
