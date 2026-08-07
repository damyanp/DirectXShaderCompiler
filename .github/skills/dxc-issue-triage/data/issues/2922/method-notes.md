# Method notes from #2922

Observations about the *method and tooling*, not about the issue. Recorded here for collation;
SKILL.md is not edited by per-issue workers.

---

## 1. `cmd.txt` cannot express a two-stage repro, and `bisect` will still answer

`run` executes `[exe] + shlex.split(line)` per `cmd.txt` line — one **dxc** invocation. #2922's
symptom lives in a PIX pass (`-dxil-dbg-value-to-dbg-declare`) that only `IDxcOptimizer`
exposes; `dxc.exe` never runs it. The fix touched *only* that pass, so dxc's output is
identical on both sides of it and **no predicate over dxc's stdout can see this bug**.

The trap is that `bisect` still returns a confident-looking answer. Here it said
`regressed-in v1.6.2104 (last good: v1.5.2010)` — which is where dxc first emitted
`DILocalVariable` for this shader, i.e. where the *precondition* appeared. Wrong direction
(the bug was fixed, not introduced) and wrong date. This is the `invalid-probe` failure mode
one layer out: the probe ran fine, it just measured a different thing.

Nothing in the tooling flags "your predicate is constant across the transition you are
looking for". A cheap heuristic that would have: **if the primary predicate scores the same on
both bisect endpoints AND the recorded status disagrees with the ground-truth probe's verdict,
warn.** #3005 hit the same shape (predicate ≠ symptom) and solved it the same way, by
documentation in `match.json`'s `note`; it is now at least the second occurrence, so it may be
worth a `match.json` field — e.g. `"measures": "precondition"` — that `reindex`/`overview`
could render, instead of relying on every future reader opening the note.

## 2. `dxopt -external` triages any `IDxcOptimizer`-only pass across releases

Generally useful, and not in SKILL.md. Release packages ship only `dxc.exe`,
`dxcompiler.dll`, `dxil.dll` — no `opt.exe`, no `dxopt.exe`. But a **locally built**
`dxopt.exe` can be pointed at any release's DLL:

```
dxopt.exe -external <release>/bin/x64/dxcompiler.dll -external-fn DxcCreateInstance \
          -o=out.bc in.ll -opt-mod-passes -dxil-dbg-value-to-dbg-declare ...
```

so the *release's* pass runs while `dxopt` is only marshalling blobs. That makes the whole PIX
pass family (and anything else reachable only through `IDxcOptimizer`) bisectable across
releases. Local `opt.exe` is **not** a substitute — it does not link the PIX passes and reports
`Unknown command line argument '-dxil-dbg-value-to-dbg-declare'`. It is fine as a plain
bitcode disassembler, including for bitcode written by release DLLs as old as v1.5.2010.

Two `dxopt.exe` argument-parsing traps, both of which fail as
`Operation failed - error code 0x80070057` (E_INVALIDARG) and both of which look exactly like
the pass rejecting the module:

1. **`-external` requires `-external-fn DxcCreateInstance`.** Without it `dxopt.cpp` does
   `CW2A externalFnA(externalFn)` on a null pointer, and *everything* fails — even `-passes`.
2. **`-o=OUT` must come before the input file.** The argument loop `break`s at the first
   file-input argument and treats everything after as optimizer arguments, so a trailing
   `-o=...` is handed to `RunOptimizer`.

## 3. A near-miss discriminator: `!pix-alloca-reg-write` is present in the broken output

The natural-looking observable for "did the PIX annotation passes do their job" is
`!pix-alloca-reg-write`. On this issue it would have reported the defect as **absent**:

| build / level | `!pix-alloca-reg-write` tags | `llvm.dbg.declare` instructions |
| --- | --- | --- |
| v1.6.2112 `-Od` (healthy control) | 2 | 1 |
| v1.6.2112 `-O1` (**the bug**) | 2 | 0 |
| main `-O1` (fixed) | 4 | 2 |

Pre-fix, the two tags sit on the stores into the shader's own `%p1` alloca, which exist
regardless. A `contains "!pix-alloca-reg-write"` predicate matches the broken output. Even the
*count* is ambiguous: 2 means both "healthy `-Od`" and "broken `-O1`".

Generalisation worth carrying: when a pass's product is *added* IR, count the thing the pass
creates (here `llvm.dbg.declare`, which is also exactly what `PixTest` walks), not metadata
that decorates IR the pass did not create.

## 4. `godbolt-note.txt` is embedded verbatim into the DXIL, and poisons text matching

DXC records the full source in module metadata (`!dx.source.contents`). `annotate()` prepends
`godbolt-note.txt` to the published source, so **every line of the banner appears verbatim
inside the compiled output**. My first banner contained the example line
`call void @llvm.dbg.declare(metadata %struct.smallPayload.0* %p, ...)` as a "what to look
for" hint, and a text count over the pane output then reported one `llvm.dbg.declare` in a
pane that has none.

This did not affect the verdict — `match.json` is scored on locally compiled *unannotated*
`repro.hlsl` — but it is a live hazard for anyone who scores CE output, diffs panes, or greps
a captured pane. Two mitigations, and I ended up applying both: keep literal IR out of the
banner (the banner now writes `llvm.dbg.value(metadata …)` without the `call void @` prefix),
and restrict counting to instruction lines. `manual-case-godbolt-panes.txt` explains it in
situ. Worth a line in SKILL.md's step 7: **the banner is compiled, not just displayed.**

## 5. `invalid-probe` needs a *feature-presence* control, and here it caught a second one

SKILL.md's `invalid-probe` examples are mostly "the release rejects the profile" — loud and
obvious (v1.4.1907: `error: invalid profile as_6_5`). v1.5.2010 was the quiet kind: it
compiles the repro **successfully, exit 0**, and produces IR that simply contains no
`DILocalVariable` and no `llvm.dbg.*` record for the local at any optimisation level. The pass
therefore has no input, and its behaviour on that release is not evidence either way.

Nothing about the run says so. What identified it was measuring the **`-Od` control on the
same release**: every release from v1.6.2104 onward emits exactly 1 `llvm.dbg.declare` at
`-Od`; v1.5.2010 emits 0. Without that per-release control, v1.5.2010 would have been recorded
as "no-repro" and would have shifted the apparent history by a release. Worth stating as a
rule: **run the feature-presence control on every probed release, not only on ground truth** —
a control that only exists at HEAD cannot detect a release that silently lacks the input.

(I spent time chasing a false lead here: an early ad-hoc PowerShell probe appeared to show
v1.5.2010 emitting `llvm.dbg.declare` when `/Qembed_debug` was dropped. It was output
interleaving from three `Write-Host`-separated blocks in one command — the lines belonged to a
different release's file. A controlled re-run over seven flag combinations showed v1.5.2010
emits zero debug records in all of them. **Do not read multi-block PowerShell output
positionally; label every line with its source file.**)

## 6. The blind reproducibility check earns its cost on *unsupported*, not *wrong*, claims

SKILL.md mandates it for `close-fixed`. On #2922 it reproduced all five verdict fields and
both `invalid-probe` rejections — and then found three defects, none of which changed the
verdict and none of which I would have found by re-reading my own work:

* a `--stat` summary paraphrased from memory as "touched `lib/DxilPIXPasses` only" when the
  commit touched four files;
* "panes 1 and 2 are identical" where the metadata node numbers differ;
* an echoed `$ git tag --contains … | sort -V` command line in a capture that was **not the
  command actually run** — the output was `git tag`'s lexicographic order.

All three are the same species: a claim written *around* evidence rather than *from* it. The
third is the serious one, because a `$ ` line in a `manual-case-*.txt` is an assertion that
the text below it came from that command, and a reader has no way to check. Suggested
addition to the method: **generate `manual-case-*.txt` from a script that echoes the command
it is about to run, never by transcribing.** `measure.py`'s `report()` does this; the hand-run
git capture did not, and that is exactly where the error appeared.
