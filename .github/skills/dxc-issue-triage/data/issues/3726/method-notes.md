# Method notes from #3726

Things learned about the *procedure*, not about this issue. Candidates for promotion into
`SKILL.md` at collation. Each one is stated with the measurement that produced it.

---

## 1. A `file:line:col: error:` prefix does **not** mean the front end produced it

This is the single biggest trap in this issue's shape, and it fails in both directions.

`dxilutil::EmitErrorOnInstruction` maps an LLVM debug location back to source, so DXC's
**DXIL backend** prints a fully source-located, caret-annotated diagnostic:

```
repro.hlsl:15:10: error: local resource not guaranteed to map to unique global resource.
    a0 = r0;
         ^
```

That is emitted from `lib/HLSL/DxilCondenseResources.cpp`, ~150 passes after code
generation. And on **v1.4.1907** the *same* error prints with no location at all, plus
`Use /Zi for source location.` — so the presence *or* absence of a location prefix says
nothing about the layer, and it varies by release for a fixed layer.

**Rule: never attribute a DXC diagnostic to a layer from its printed shape.** Attribute it
from the emitting site in the tree, or from a flag that stops before the layer in question.

## 2. `-fcgl` is the instrument for "did the front end diagnose this?"

`-fcgl` emits the front end's high-level IR and never runs DXIL lowering, so a clean `-fcgl`
run *is* the statement "Sema had nothing to say". It is supported as far back as **v1.4.1907**,
so it works across the whole bisectable range. Any "should this have been diagnosed earlier"
issue should put an `-fcgl` line in `cmd.txt` on day one; it converts an inference into a
measurement, and it costs one line.

## 3. `-Zs` is **not** a syntax-only flag in DXC

`-Zs` means "generate small PDB with just sources and compile options". It runs a **full**
compile. It was reached for first here as the front-end-only probe (by analogy with clang's
`-fsyntax-only`) and silently answered a different question — it "confirmed" a front-end
error that was actually the backend's. Nothing in the output distinguishes the two cases.

## 4. `dxc -Odump` prints the pass pipeline — use it to attribute a message to a pass

Finding the string in `lib/HLSL/` gives you the file; `-Odump` for the profile under test
tells you whether that pass actually runs for this shader and roughly where. That is what
turned "this string lives in DxilCondenseResources.cpp" into "this is reported from
`-hlsl-dxil-lower-handle-for-lib`, long after `-dxilgen`", which is the claim the issue is
actually about.

## 5. A multi-invocation `cmd.txt` lets one invocation contaminate **every** predicate's
   classification of the capture

`cmd.txt` here has three lines (DXIL / SPIR-V / `-fcgl`). On v1.4.1907 the SPIR-V line
prints `SPIR-V CodeGen not available`, a feature-absence marker. `classify()` demotes the
whole capture to `invalid-probe` — including for `match-sema.json`, which is about the
`-fcgl` line and whose own invocation ran perfectly.

This is not a bug in the tool (it cannot know which invocation a predicate is about), but it
**silently shrinks the history window of an unrelated predicate**. Mitigation used here:
capture the affected invocation on its own and commit it beside the demoted one
(`variant-fcgl-only-v1.4.1907--match-sema.txt`), so the datapoint the demotion discarded is
still on disk and quotable. Predict this in the predicate's `note` *before* running the
scan, so the demotion reads as confirmation rather than as a surprise.

## 6. A control run with `--args` that changes the profile can be **vacuously** clean

`match-sema.json`'s regex anchors on `\$ dxc -T ps_6_0 -E main -fcgl` in order to pin which
invocation it is reading. A control captured with `--args "-T cs_6_0 ..."` therefore could
never match, and its `no-match` proved nothing at all. It was captured, spotted, deleted and
replaced.

**Rule: when a predicate anchors on the command line, every control must use a command line
the anchor can match.** Before believing a `--expect no-match` control, check that the
predicate *could* have fired on that capture.

## 7. Absence checks need a positive control **over the same paths with the same tool** —
   and the control can fail too

The intended claim was "no front-end source contains the backend's message". First attempt:

```
git grep -l "local resource not guaranteed" -- tools/clang/
```

which matched ~30 files — all FileCheck **tests** asserting the backend's output. Narrowing
to `tools/clang/lib/` gave a clean result, so a positive control was added over the same
scope… and **it also returned nothing**, because DXC's diagnostic *text* lives in
`.td` files under `tools/clang/include/`, not in `lib/`. The control caught a scope that
could not have answered the question either way.

Final scope `tools/clang/lib/ tools/clang/include/`, with
`git grep -l "cannot %0 from resource containing"` as the positive control (matches
`DiagnosticSemaKinds.td`). **The point: a positive control is not a formality. It failed
here, and it failed in a way that would have produced a confident wrong claim.**

Related, and confirmed again: the agent `grep` tool returns "no matches found" with no error
when no `glob` filter is passed. Every absence check in this issue used `git grep` or
`Select-String`.

## 8. Generate `manual-case-*.txt` from a committed script that echoes its own commands

Already in SKILL.md; worth reinforcing with two new uses. Both
`make-sema-absence.py` (source corroboration) and `make-clang-control.py` (the CE control
matrix) print `subprocess.list2cmdline(argv)` / the exact POST payload fields before each
result, derive all paths from `__file__`, and are committed next to their output. When the
`tools/clang/` scope above turned out to be wrong, fixing it was a one-line edit and a
re-run rather than a hand-editing exercise on a transcript.

Corollary discovered while writing one: **a summary line that greps its own output for
"error" will match the source echoed back by the compiler.** DXC embeds the whole shader in
`!dx.source.contents`, and this file's own header comment mentioning "error" was reported as
the first error line of a clean compile. Require the `error:` spelling and skip lines
starting with `!`.

## 9. For a Clang pane, run the control **through the same API**, not by eye

`triage.py godbolt` publishes and verifies the link, but it does not tell you whether Clang
could have compiled a *working* version of the same shader. A 2×2 matrix — {trivial control,
repro} × {dxc_trunk, hlsl_clang_trunk}, identical arguments — is ~60 lines of `urllib` and
turns "Clang accepts it" from an anecdote into a controlled result. Here it mattered: Clang
accepting the repro is the headline finding, and it is only believable because the control
shows Clang compiling the same stage and resource type cleanly.

`-fsyntax-only` was not needed. Reach for it only when Clang's **backend** is the obstacle;
if the control compiles end-to-end, don't weaken the comparison.

## 10. `ce_args` warns "multi-invocation cmd.txt; linking the first only"

With a multi-line `cmd.txt`, CE gets line 1's arguments. If the published source is a
restatement needing a different profile (compute here, vs. the pixel-shader `cmd.txt`), the
default is silently wrong. Pass explicit `id:<args>` overrides for **every** pane in that
situation — and note that repeating the same compiler id with different args is a legitimate
way to put `-spirv` next to DXIL in one link:

```
dxc_1_6_2112:-T cs_6_0 -E main,dxc_trunk:-T cs_6_0 -E main,\
dxc_trunk:-T cs_6_0 -E main -spirv,hlsl_clang_trunk:-T cs_6_0 -E main
```

The shortlink read-back confirmed all four panes, in order, with distinct args.

## 11. `godbolt-note.txt` shifts every line number the panes report

The banner is prepended to the source, so `<source>:50:10` on CE corresponds to line 19 of
`repro-cs.hlsl`. Harmless, but a reader comparing the CE pane against the committed repro
will be confused if the write-up does not say so. Say so.

## 12. "Which layer?" issues want a **layer × release** table, not just a verdict

`make-layer-history.py` reads only the committed captures — it runs no compiler — and prints
one row per release with a column per layer (DXIL exit / message present / SPIR-V exit /
what SPIR-V bound / `-fcgl` exit / `-fcgl` diagnostics). It is the most quotable artefact in
this directory, and it is derived rather than transcribed, so it cannot drift from the
evidence. It also made the SPIR-V finding visible: the "SPIR-V binds" column reads
`x0+x1+x2` on every release, which is not something a pass/fail predicate would have shown.

Generalisation: when an issue is about *where* or *how* something is diagnosed rather than
*whether*, one predicate is not enough to express the finding. Add a derived table.

## 13. Check whether a maintainer's correction changes the answer — before adopting it

The standing 2024 comment says the repro's globals "should be static". With `static`, DXC's
DXIL path compiles **cleanly** — the opposite result. Had the `static` form been adopted as
"the real repro", the verdict would have been `cannot-reproduce`.

**Rule: treat a maintainer's restatement as a variant to test, not as a correction to
apply.** If it behaves differently from the as-filed text, that difference is a finding and
belongs in the comment — a future reader will otherwise hit it and conclude the issue is
stale.

(It also generated a genuinely new defect: the `static` form's SPIR-V output has *no*
resource variables at all, just `OpUndef` for the image, sampler and pointer types.)

## 14. Read the issue **timeline** before proposing labels — a removal is a decision

`spirv` was the obvious label to propose here: the issue explicitly raises the SPIR-V
backend, and SPIR-V turned out to be the worse half. The timeline says otherwise:

```
gh api repos/microsoft/DirectXShaderCompiler/issues/3726/timeline --paginate
  2021-04-29  jaebaek  +spirv   (issue titled "[SPIRV] do not allow assignment to resource")
  2024-07-16  damyanp  +incorrect-code
  2024-07-16  damyanp  -spirv
  2024-07-16  damyanp  renamed  ->  "Sema should not allow assignment to resource"
```

`spirv` was removed **in the same minute as the retitle**, as a deliberate reframing.
Proposing it back would have silently reversed a maintainer decision — and the proposal
would have looked well-supported by the evidence, which is what makes it dangerous.

Two general points:

* The `labels` field on `issue.json` is a snapshot; the timeline is the *argument*. A
  proposed addition should be checked against `labeled`/`unlabeled` events for that exact
  label before it is recorded.
* A rename event is also the cheapest possible `text_stale` check. Here it cut the other
  way: the title was updated in 2024 to say precisely where the defect is, which is direct
  evidence *against* staleness.

Same call applies to `milestoned` — this one sits in `Backlog`, which is context a
suggested action of `still-valid-keep-open` should be consistent with.

## 15. `triage.py verdict` is incremental — fixing one field does not require re-passing all

`verdict --issue N --labels-add "..."` on its own printed `2 field(s) recorded` and left the
other 11 untouched. Useful when a late finding (the timeline above) invalidates one field of
an already-recorded verdict; re-running the full command risks a transcription error in the
long `--summary`.

Related PowerShell hazard, confirmed: build any `--summary` containing `$`, backticks or
`"` as a **single-quoted variable first**, then pass `$sum`. Escaping it inline is where the
quoting breaks.

## 16. Two predicates with opposite polarity is the right tool for "fixed vs. changed shape"

`match.json` (positive: the backend error) and `match-sema.json` (**inverted**: a match would
mean the front end learned to diagnose it) were bisected separately. That is what allows the
history to say two different things at once — "the backend has always rejected this" and
"the front end has never diagnosed it" — instead of collapsing them into one ambiguous line.

The cost is that **the inverted predicate must restate its polarity everywhere its history
is quoted**, because `never-repro'd` reads as good news and here means the opposite. It is
restated in the predicate `note`, in `notes.md`, and in the verdict summary.
