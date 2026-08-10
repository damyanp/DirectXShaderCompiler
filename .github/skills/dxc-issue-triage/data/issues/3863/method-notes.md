# Method notes from #3863

Candidates for promotion into `SKILL.md` at collation. Each is written so a
later session can tell whether it generalises or was local to this issue.

## 1. A neighbouring issue's *source reading* is a hypothesis, not evidence

#3044's method note 8 recorded, from reading `dxcompilerobj.cpp`, that
preprocessing "treats preprocessing as an exclusive mode with a hand-built
`PreprocessorOutputOptions`, which is both why no driver flag reaches
`ShowComments` and why `-H` cannot run alongside `-P`."

The first half is right. The second half is **wrong**, and measuring it was the
single most valuable thing this triage did. `-H` *does* run alongside `-P`:
`EnableDisplayIncludeProcess()` is called before the `isPreprocessing` branch,
the trace is generated, and it is stored on the result object as
`DXC_OUT_REMARKS`. `manual-case-api-remarks.txt` reads it back through
`IDxcCompiler3::Compile`. What is missing is one line in
`DxcContext::Preprocess()`.

The difference matters to a maintainer: "these two issues share a root cause"
would have grouped a missing feature with a dropped output and invited one fix
for two unrelated problems. Generalisation: **inherit a neighbouring issue's
*measurements* freely; re-derive its *explanations* before building on them.**
An explanation that was never load-bearing for that issue's verdict was never
tested by that issue's controls.

## 2. Reach past the driver when the driver is the suspect

The command line is one consumer of the compiler. When the symptom is "the tool
printed nothing", driving `dxcompiler.dll` directly through `IDxcCompiler3`
distinguishes *not computed* from *computed and not printed* — a distinction
that changes the verdict's meaning (feature request vs dropped output), the
size of the fix, and the label.

ctypes is enough; no build step. What made it trustworthy was the pair of
controls: the same API call **without** `-H` (REMARKS present but empty, so a
positive is not "REMARKS is always there") and a **non-`-P`** compile with `-H`
(trace present, so a negative is not "this harness cannot see REMARKS").

One trap worth recording: passing a NULL `IDxcIncludeHandler` makes every
`#include` fail with `ERROR_NOT_FOUND`, which yields an empty trace for reasons
that have nothing to do with the issue. Use
`IDxcUtils::CreateDefaultIncludeHandler`. The self-evident-looking measurement
would have quietly confirmed the wrong answer.

## 3. `not_regex` needs a control that makes it fire, in the same shape

A clause asserting "`Opening file [` never appears for `inc-pp-*.h`" passes
just as happily when the compiler crashed, when the wrong file was compiled, or
when the predicate has a typo. The control here was to run the **same file,
same headers, same flag, without `-P`** (`variant-h-on-compile-of-repro`,
`--expect no-match`) and watch the clause fail. That is the only version of
this control that isolates the one variable.

## 4. Anchor absence predicates on the *syntax*, not on the name

`inc-pp-a.h` appears in the preprocessed output as a `#line` marker, and the
capture embeds that output. A `not_regex` searching for the header *name* would
have found it and reported the bug fixed. The clause must anchor on the literal
`Opening file [` prefix. Generalisation: when a repro's own filenames appear in
the artifact under test, an absence predicate must key on the *form* of the
message, not on any token the artifact can legitimately contain.

## 5. `run --shader` is unusable for a multi-invocation `cmd.txt`

Independently re-hit here, so #3044's finding generalises: `retarget_cmd`
(`triage.py:925-944`) exits with `no source file to replace in: <line>` for any
line without a `.hlsl` token. This issue's chain ends
`-T ps_6_0 -E main -Zi preprocessed.i`, which has none — the whole point of the
third invocation is to compile the *preprocessed* artifact. Every variant here
had to be `run --args` with a complete argv. Two independent hits in two
batches suggests the fix (skip lines with no source, or retarget only the lines
that have one) is worth making rather than documenting.

## 6. "Exit 0 means it was accepted" is only true for `-`-prefixed flags

SKILL.md's `/ZZZNONSENSE` trap says exit 0 proves nothing, because dxc silently
treats an unknown `/flag` as an input path. The inverse is also worth stating:
for a `-`-prefixed flag dxc **does** diagnose
(`dxc failed : Unknown argument: '-ZZZNONSENSE3863'`, exit 1), so silence *is*
informative — provided the probe demonstrates it in the same position on the
same command line. Doing so costs one variant and converts "exit 0, who knows"
into "parsed, then ignored", which is a materially different report. The
predicate must quote `Unknown argument` verbatim so `_predicate_quotes()`
suppresses the invalid-probe demotion and the automatic spelling re-probe;
otherwise the capture records a re-spelled command instead of the rejection.

## 7. Record a CE skip by measuring it, not by reasoning about it

The skip reason here is three CE API calls (`manual-case-ce-infeasible.txt`),
not an argument. It was worth doing: the *interesting* finding was case 1 — with
no `#include` at all, `-H` prints nothing, so a single-source pane cannot show
the **working** case either. Reasoning alone would have stopped at "CE is
single-source, so the header is missing" and might still have published a link
showing an empty pane, which a reader cannot distinguish from a failed run.
Generalisation: for any issue whose symptom is *absence*, ask first whether CE
can display the corresponding *presence*. If it cannot, the link is unfalsifiable
and a `--skip` is the honest artifact.

## 8. Date a workaround with the same sweep that dates the symptom

The release matrix already visits every release; adding two columns for the
suggested alternative (`-M` on a compile, `-M` under `-P`) cost nothing and
produced the two facts most useful to the reporter: `-M` has been available
since **v1.7.2207**, and it has **never** worked under `-P`. That turns "there
is a workaround" into "there is a workaround, from this version, with this
limitation" — and incidentally confirms the adjacent open issue 4723 without
triaging it.

## 9. Adjacent defect met in passing, not triaged

With an unresolvable `#include`, a normal compile fails with `0x80004005`;
`-P` prints the same `fatal error: … file not found`, writes no output file,
and exits **0**. Distinct from this issue and left alone, but it is the kind of
thing a preprocessor-area sweep should look for deliberately, and it is close
in spirit to referenced open issue 5117.

## 10. Grammar-aware history is now a reusable pattern, not a one-off

#3044 wrote a bespoke matrix because `-P`'s grammar changed at `8bf2b087c`.
This issue needed the same thing and the script was rewritten from scratch. The
reusable core is small and generalises to any option whose *spelling* changed
mid-history: probe each release for which spelling it accepts, record the answer
as data, and refuse to proceed with a release that accepted neither. The
changeover this run measured (old ≤ v1.7.2207, new ≥ v1.7.2212) brackets the
commit exactly, which is a free self-consistency check on the whole sweep —
worth asserting explicitly rather than eyeballing.
