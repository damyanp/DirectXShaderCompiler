# Method notes from #4701

Lessons about the *method*, not about this issue. #4701 is a **code-quality** report — the
compiler is accused of failing to optimise, not of being wrong — and most of what follows
comes from that shape not fitting the default pass/fail machinery.

---

## 1. A code-quality issue needs a paired matrix; `bisect` alone cannot give you one

`bisect` walks one shader across releases. On a correctness bug that is enough: the shader
either miscompiles or it doesn't. On a missed-optimisation report it is **structurally unable
to answer the question**, because "still dirty on every release" is consistent with two very
different stories:

* the reported case never got optimised (a persistent gap), and
* the reported case never got optimised *but the comparison case only recently started
  getting optimised* (a widening gap, or an asymmetry that is newer than it looks).

You cannot tell them apart from one arm. The fix is cheap: run the reported case **and** a
reference case you expect to optimise well across the *same* releases with the *same*
instrument, and read the pair. Here `release-matrix.py` ran five shaders × 21 compilers; the
`static` arm being clean on v1.4.1907 (2019) is what turns "reproduces everywhere" into
"a groupshared-specific gap that predates the report", which is a much stronger statement and
was not available from `bisect` output.

Generalisation: **any issue whose claim is comparative needs a comparative history.** That
includes performance, code size, diagnostic quality, and "X works but Y doesn't" reports.
Worth considering as a `bisect --paired` mode, or at least a documented recipe.

## 2. Both arms must be measured by the *same* instrument

The obvious mistake is to write one predicate for the reported case (`addrspace(3) global`)
and eyeball the other. Then the two arms are not comparable and the "reference case is clean"
claim is unfalsifiable. `match-deadarray.json` exists purely to be address-space-agnostic —
"a `[10 x float]` module global survives AND some `store` survives" — so the same regex pair
scores both arms. The address-space-specific `match.json` stays as the primary predicate
because it is the issue's actual claim.

Two predicates over one issue is not redundancy; it is the difference between a measurement
and an impression.

## 3. Fields printed by the compiler are *instruments*, and instruments change

`main` prints `; NumBytesGroupSharedMemory: 40` for the repro and `0` for the reference case.
That is a beautiful metric — user-visible, numeric, exactly the thing the report is about —
and putting it in a predicate would have been a **silent disaster**: the field does not exist
in any catalogued release, so every release would have scored "clean" and the tool would have
reported a regression landing precisely at the newest thing measured.

The general trap: when a metric comes from the compiler's own reporting layer (PSV, RDAT,
reflection, disassembly comments, `-Zi` metadata, statistics counters), a change in the metric
across releases is ambiguous between *behaviour changed* and *the instrument changed*.

The disambiguation is a **fixed-reader cross-check**: hold the reader constant (the newest
disassembler), vary only the producer, and re-read old releases' containers with the new
reader. If the field is still absent, the field was never in those containers — an instrument
change. `tgsm-crosscheck.py` does this in ~60 lines and is worth generalising.

Related and worth stating explicitly: **a bisection floor is a suspicious place to find a
regression.** If the "change" lands at the oldest or newest measurable point, suspect the
instrument before believing the result.

## 4. "Not optimised" needs a countable definition, chosen before looking

An eyeball diff of two IR dumps is not a verdict and does not survive being read a year later.
What worked: pick countable structural facts (how many address-space-3 `[10 x float]` globals;
how many address-space-3 stores), write them into `expected.md` *before* running anything, and
make the predicate test exactly those. Then "repro" has a definition that someone else can
re-derive and disagree with.

Instruction *counts* are the tempting alternative and are worse for this: they drift with
unrelated codegen changes across a 6-year release span, so a count-based threshold would have
manufactured differences between releases that have nothing to do with the issue.

## 5. Presence-clause predicates need an anti-vacuity anchor *and* a positive self-test

Both of this issue's clauses are presence clauses ("the global is still there", "the store is
still there"). Absence therefore has two possible causes — the optimiser removed it, or
nothing was emitted at all — and they must be separated:

* **anchor** (`!dx.entryPoints` + exit 0) proves a real module was produced, so a failed
  compile cannot score as "optimised";
* **positive self-test** (`control-gs-live.hlsl`, a groupshared array that genuinely *is* read
  back, declared `--expect match`) proves the regexes can still see the thing when it exists.

The self-test is the one that pays off across releases: it converts "no match on v1.5.2010"
from an assumption into a measurement. Without it, an IR spelling change in any release would
look like a fix.

## 6. A missed optimisation is much stronger with a *consequence pair*

"The compiler emits four extra bytes of IR" is easy to deprioritise. The same defect scaled
until it changes compile **success** is not: identical dead arrays at 64 KB, differing only in
storage class, give a DXIL validation failure vs. an empty `main`. That single A/B did more
for the write-up than the entire release matrix.

Generalisable recipe for code-quality issues: find the smallest input where the missed
optimisation crosses a **hard limit the compiler itself enforces** (resource budgets,
instruction-count limits, register/TGSM budgets, unroll bounds) and show the boundary. Keep it
framed as *consequence*, not as a second bug — whether the budget check should run after such
an optimisation is a design decision, and pre-empting it would be exactly the over-reach the
skill warns about.

## 7. Exit code shapes, again

`0x80004005` (2147500037) came back from the 64 KB case and is E_FAIL for an ordinary
diagnosed validation failure. Nothing crash-shaped about it. Worth repeating because the
temptation is strongest exactly when the output is dramatic (a 64 KB allocation blowing a
budget *feels* like a crash report).

## 8. Compiler Explorer specifics

* **CE gives every pane one shared source.** A one-variable A/B is therefore expressed with
  `#ifdef` plus a `-D` on one pane's args — not by two links. `ce_compiler_specs` builds a
  *list*, so the same compiler id can legitimately appear more than once with different args;
  this issue used `dxc_trunk` and `hlsl_clang_trunk` twice each.
* **`godbolt --source X` needs explicit `id:<args>` for every pane**, not just the changed one.
* **CE appends `-Zi -Qembed_debug` to DXC panes**, so any explanatory banner in the source is
  compiled into `!dx.source.contents` and will appear in the pane output. If the banner
  contains the same tokens the reader is being asked to look for, it manufactures apparent
  hits. Write the banner to *avoid* the literal tokens under test (here: `addrspace(3)`,
  `[10 x float]`, `store float`) and then verify it did not match.

## 9. Check the successor compiler before proposing `check-in-clang`

`hlsl_clang_trunk` is on Compiler Explorer and takes `-T`/`-E`, so "does this also affect the
clang-based front end?" is a two-minute measurement rather than a label asking someone else to
do it. Here it reproduces identically, which is a materially more useful finding than the
label would have been — and it means `check-in-clang` should *not* be proposed. Worth making
this the default step for any issue where the label is a candidate.

## 10. Evidence that only exists in the terminal does not exist

Three claims in this write-up were true, measured, and **not on disk** until a late sweep
caught them: the `-fcgl` output for the reference arm (the linkage/initializer contrast that
carries the whole root-cause argument), the `-Odump` pass listing, and `dxc --help`'s
statement of the default optimisation level. Each had been observed in an exploratory run and
then cited from memory.

Cheap habit that catches it: before writing the verdict, grep the issue directory for the
distinctive strings the notes quote (`internal global`, `-globalopt`, `Default`). Anything the
notes assert but the directory cannot show is either re-run or deleted from the notes.

## 11. Adjacent issue, for collation to judge

`gh search issues` surfaced **#6417** (open, `bug`/`matrix-bug`, 2024-03-14): partially-dead
stores into a groupshared struct that *is* otherwise live. Same area (dead stores to TGSM),
different defect (#4701 is a wholly-dead allocation; #6417 is partial deadness inside a live
one), and a fix for either would not obviously fix the other. Recorded here rather than in
`comment.md` because cross-issue claims are collation's call.
