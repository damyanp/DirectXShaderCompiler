# Issue 4721 — method notes

Things that went wrong, or nearly did, and what they cost.

## 1. A `--shader` control inherits every line of `cmd.txt`

Two controls came back `invalid-probe` instead of the declared `no-repro`.
Cause: `cmd.txt` here has two lines, and `run --shader X` substitutes the
shader into **both** — including the `-fixit` line, whose output is
`dxc failed : Unknown argument: '-fixit'`. `classify()` treats
`unknown argument` as a feature-absence marker and demotes the capture, unless
the issue's predicate quotes that text verbatim. `match.json` does quote it;
`match-hint.json` deliberately does not, because it is scored on the *hint*,
not on the flag. So the control was demoted by a line that had nothing to do
with what it was controlling.

Two fixes exist: `"quote_from": ["match.json"]` in the secondary predicate, or
`--args` naming only the relevant invocation. I used `--args`, because the
`-fixit` line is genuinely irrelevant to a hint-rendering control and dropping
it makes the recorded command match the question being asked.

**Generalisable:** with a multi-line `cmd.txt`, a `--shader` control is scored
on the union of all lines. When a secondary predicate deliberately ignores one
of those lines, use `--args`.

## 2. Marker ordering makes the release search look cleaner than it is

`classify()` finds the *first* feature-absence marker in the combined capture.
Line 1's `Unknown argument: '-fixit'` always precedes line 2's
`Unknown HLSL version: 2021`, and `match.json` quotes the former — so a
release that cannot express the repro at all scores a plain `no-repro` rather
than `invalid-probe`.

Consequence: **the bisect line is not capability history.** Read
`manual-case-release-matrix.txt` column (c) instead, which asks each build
directly whether it accepts `-HV 2021`.

## 3. The control that was wrong for eight releases — caught by running it

The matrix's probe-validity control was originally `control-fixed.hlsl`, on
the reasoning that a build which compiles the corrected form can express the
repro. It failed on v1.6.2112–v1.8.2407, which would have labelled ten
probeable releases "cannot express HLSL 2021" and thrown away most of the
hint-history evidence.

It was not an HLSL-2021 failure at all: those releases cannot compile
`and(...)` (`Invalid record`, also under `-Vd`), while a trivial shader builds
fine under `-HV 2021`. One control was silently answering two questions.

Split into `control-hlsl2021.hlsl` (deliberately boring — no intrinsic whose
availability varies) for probe validity, and `control-fixed.hlsl` kept as its
own column, since "does dxc's own suggestion compile?" turned out to be worth
knowing. The script now self-tests that the two columns disagree, because if
they ever agree everywhere the split has stopped earning its place.

**Generalisable:** a control that fails is not automatically doing its job. It
has to fail *for the reason you think*, and a control built from the repro's
subject matter tends to inherit the repro's dependencies.

## 4. A clean exit is not a result

`dxc /fixit x.hlsl` exits 0, and so does `dxc /ZZZNONSENSE x.hlsl`. Unrecognised
`/`-flags are dropped silently. The exit code cannot distinguish "honoured"
from "discarded", so `probe-flag-spellings.py` compares SHA-256 of the
compiled object instead — and includes a flag that *is* honoured
(`-Zi -Qembed_debug`) whose hash must differ. Without that row, three matching
hashes are equally consistent with an instrument that cannot see anything.

Related: `/`-flags cannot be tested on Compiler Explorer at all, because CE's
Linux builds read a leading `/` as a path. That evidence has to be local.

## 5. Trying the Clang pane changed the verdict's usefulness

A pure feature request is a legitimate `godbolt --skip`, and I nearly took it.
Adding an `hlsl_clang_trunk` pane with `-Xclang -fixit` turned the write-up
from "not implemented" into "implemented upstream, unreachable here" — with
`note: FIX-IT applied suggested code changes` as proof. The four-pane link
(pre-hint release, hint, flag rejected, clang applying it) is the whole
finding in one URL.

The pane's *first line* is a `-Qembed_debug` warning; the result is further
down. Read `manual-case-godbolt-verify.txt`, never the console summary.

## 6. A different model found three unverbatim quotes

Step 10's cross-model review of the drafts caught what self-review would not
have: two "verbatim" quotations in `comment.md` that were reconstructions
rather than copies — `error: validation errors / Invalid record` collapsed two
capture lines into one with a slash, and the CE `FIX-IT` line did not appear
in any capture as written, because Compiler Explorer returns **ANSI-colourised
diagnostics** and the escapes sit inside the text.

Fixes: `probe-clang-fixit.py` now strips SGR escapes (and says so in the file
header), so a line quoted out of it is the line that is in it. Two further
claims — `-Vd` still failing, and `-help` listing none of the spellings —
were true but had only been observed in ad-hoc shell calls, never captured;
they are now columns in `release-matrix.py` and `probe-flag-spellings.py`
respectively, the latter with a self-test that the same search *does* find a
flag that is documented.

**Generalisable:** "I ran it and saw it" decays into "I remember it" by the
time the write-up is drafted. If a sentence in the comment asserts a
measurement, the measurement needs a file. And a quotation should be produced
by copying from that file, not by retyping what it said.

`check-quotes.py` now enforces the second half of that mechanically: it pulls
every fenced-block line and every output-shaped inline span out of
`comment.md` and requires each to occur in some capture in this directory
(ANSI stripped). It found its own first bug immediately — a `` ` `` scan over
the whole file pairs the ``` fences with each other and swallows whole blocks
— and a second on the next pass: the check's own output file lists the strings
it is checking, so leaving it in the haystack made every quote match itself.
Both are the same failure mode as the thing being checked: a test that cannot
fail looks exactly like a test that passed.

The alternate flag spellings and the `-help` search are measured on the local
build only, and the comment now says "on this build" rather than implying the
release matrix covered them.

## 7. The one measurement I did not make

I did **not** build the optional `clang.exe` target to demonstrate that this
tree's own inherited `-cc1 -fixit` works. It is `EXCLUDE_FROM_ALL` and would
mean writing outside the issue directory and relinking artefacts other
concurrent workers may be using.

What it would settle: the CE evidence proves the rewriter works in
llvm-project's HLSL clang, which is a *different fork*. Building `clang.exe`
here would prove the code in **this** tree is functional and not merely
present — upgrading the claim from "linked in" to "linked in and working". The
source evidence (action, flags, CMake link line) makes that likely, but it is
inference, not measurement, and the write-up says so.
