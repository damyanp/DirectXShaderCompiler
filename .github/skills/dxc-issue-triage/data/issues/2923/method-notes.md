# Method / tooling observations from triaging #2923

Issue 2923 is a **PIX-pass** issue, not a `dxc` issue: the symptom lives in
`-dxil-annotate-with-virtual-regs`, which never runs during an ordinary
compile. Getting it under the harness surfaced a number of things that would
each have produced a wrong verdict on their own.

---

## 1. A text predicate over self-generated output needs a parse self-guard

This was the closest call in the whole issue.

My IR reader matched `llvm.dbg.declare` with

```python
r"llvm\.dbg\.declare\(metadata (\S+) (%[-\w.]+), ..."
```

`\S+` cannot match `[1 x float]*` — LLVM's type printer puts **spaces inside
the type**. The six shadow allocas that *are* the bug are exactly the ones with
that type, so the reader silently attributed zero declares to them and
**reported the reproducing case as clean**. I only noticed because the number
felt wrong, not because anything failed.

If the predicate is `contains "<marker>"` and the marker is emitted by a script
I wrote, then a bug in my script is indistinguishable from "the bug is fixed" —
and the failure direction is *toward `does-not-repro`*, which is the direction
nobody double-checks.

**Generalisable rule:** when the predicate reads output that the harness itself
produced (an analyser, a FileCheck-alike, a diff script), the producer must
emit an explicit *self-consistency* line, and the run must fail loudly when it
trips. `check-2923.py` now prints

```
llvm.dbg.declare call sites: 7, attributed to an annotated alloca: 7
```

and emits `PIX-2923: PARSE-WARNING` when those disagree. Controls alone do not
catch this class of bug: a broken reader reports *both* arms clean, and a
`--expect no-match` control passes with flying colours.

## 2. State the predicate in the quantity the *consumer* uses

`expected.md` (written before running anything, correctly) said the bug would
show as member offsets "not 0..5 **relative to the alloca base**". Measured
that way, the output is perfectly fine — every alloca's writes are 0..N-1
relative to its own base.

But `PixAllocaRegWrite::FromInst` reads `regBase` from the *referenced alloca
node* and the test asserts on `regBase + index`, i.e. the **absolute** virtual
register. Relative-correct and absolute-wrong is exactly what this bug is.

I had written a criterion that is FALSE while the bug is present. Had I not
gone back to `PixTest.cpp` and read what the assertion actually compares, the
literal reading of my own pre-registered criteria would have said
`does-not-repro`.

**Generalisable rule:** phrase symptom predicates in the units the *consumer of
the data* consumes, not the units that are convenient to read off the dump.
Verify by finding the line of code that consumes the value.

## 3. `expected.md` should be reconciled, not silently reinterpreted

Following from 2: I left `expected.md` exactly as written and reconciled it
explicitly in `notes.md` §3, criterion by criterion, saying which are false as
literally worded and why. That felt much safer than quietly adopting a new
criterion, and it is what let me notice that the *decisive* criterion — the
pre-registered "does not reproduce" clause — was unambiguously not met.
Suggest SKILL.md make that reconciliation an explicit deliverable rather than
an implicit one, since the temptation to edit `expected.md` after measuring is
strong and the edit is invisible in the artifact.

## 4. `run` / `bisect` assume a single-binary `dxc` invocation

This repro needs four tools in sequence (`dxc` → `dxa` → `dxopt` → `opt`) plus
an analyser. `triage.py` has no way to express that.

Workaround that worked, and kept every probe re-scorable by `reindex`:

* write a `run-2923.cmd` that takes the same shape of arguments as `dxc`
  (`<shader> -Od`), runs the pipeline, and prints the analyser output;
* make it answer `--version` (the harness calls it, and `resolve_compiler`
  records the string);
* register it with `triage.py compiler` under a distinct id (`main-debug-pix`)
  pointing at an **absolute** path — `subprocess.run` will only launch a `.cmd`
  by a path `CreateProcess` can resolve;
* let it take `DXC_BIN` / `PIX_DXC` / `PIX_DLL` from the environment so the
  same script can be pointed at a release build.

This is worth writing up in SKILL.md as the sanctioned pattern for
"the repro is not one `dxc` command": it costs ~30 lines and everything
downstream (`run`, `--expect`, variants, the audit) then works normally.

Caveat: **`bisect` still cannot drive it**, because `bisect` builds its own
command line from `cmd.txt` and the release's `dxc.exe`. I hand-rolled the
release matrix (`history-2923.py`) instead and recorded the result in
`--history` prose. That is a real gap; a `--compiler` passthrough on `bisect`
(substituting the release root into `DXC_BIN`) would close it.

## 5. `dxopt -external` gives you a cheap "which component changed" cross-probe

`dxopt.exe -external <path-to-old-dxcompiler.dll> -external-fn DxcCreateInstance`
runs **old passes** over **new IR** (and vice versa). A 2x2 of
{dxc 2104, dxc 2106} x {passes 2104, passes 2106} took two minutes and showed
the behaviour follows the **pass DLL**, not the front-end — which turns
"regressed somewhere in 1500 commits" into "regressed in `lib/DxilPIXPasses`".

Recommend SKILL.md mention this generally: when a transition is found, ask
whether the repro can be split across components to narrow *where* before
narrowing *when*. It is much cheaper than commit bisection and it makes the
commit search tractable.

## 6. Release-probe scripts silently overwrite the ground-truth artifacts

`history-2923.py` and `crossprobe-2923.py` write their intermediate `.ll` into
the issue directory using the same stems as the main-debug run. After running
them, the `*.annotated.ll` sitting in `data/issues/2923/` were the output of
**v1.6.2106**, not of main-debug — with no indication of that anywhere in the
file. Anyone (including me, later) reading them would have attributed
release-vintage IR to `main`.

Mitigation used: re-run the ground-truth probes **last**, after all release
probes. Better: SKILL.md should say that any artifact committed as evidence
must either name its provenance in the filename or be regenerated by the final
ground-truth run.

## 7. `bisectable=0` hides the only binary covering a 19-month window

`v1.5.2003` is marked `bisectable=0` because GitHub flags it a prerelease. The
bisectable list therefore jumps **v1.4.1907 (2019-07-15) → v1.5.2010
(2020-10-22)**. Issue 2923 was filed 2020-05-27 — squarely inside that gap.

That mattered here: `v1.5.2003` is the release that was current when the issue
was filed, and it does **not** reproduce. Without probing it explicitly I would
have had no datapoint at the report's own vintage and would have overstated the
continuity between the 2020 report and today's behaviour.

`ensure_release` will happily fetch a non-bisectable release by tag, so the fix
is procedural, not technical: **for any issue filed between 2019-07 and
2020-10, probe `v1.5.2003` by hand.** Worth a line in SKILL.md's history
section.

## 8. `invalid-probe` in this issue's shape

`v1.4.1907` cannot compile `as_6_5` at all (amplification shaders postdate it),
so it errors out and a naive text predicate scores it `no-match` — i.e. "the
bug wasn't there yet", i.e. a fabricated transition at exactly the point the
release list starts. This is the `invalid-probe` trap SKILL.md warns about, and
it is worth noting it bites *hardest at the oldest end of the list*, which is
also where a bisect wants to place its first probe. My history script prints
the raw stage-1 failure so the invalid probe is visible rather than scored.

## 9. `run` silently defaults to `main-debug`, which can be the wrong compiler

Having registered `main-debug-pix` for this issue, I later typed
`python scripts\triage.py run --issue 2923` without `--compiler`. It happily
ran plain `dxc.exe` on `repro.hlsl`, which of course produces no PIX metadata,
scored it **`no-repro`**, and wrote a `runs` row plus an `out-main-debug.txt`
capture that looks exactly like a legitimate negative result.

Nothing warned. The issue already had two `main-debug-pix` rows saying `repro`,
so the DB then held a direct contradiction whose resolution depended on knowing
which compiler was the right one. I deleted the two bad rows and the stray
capture (scoped strictly to `issue_number=2923 AND compiler='main-debug'`) and
re-ran with `--compiler main-debug-pix`.

Suggestions: when an issue has any prior run under a non-default compiler,
`run` should either default to that compiler or refuse to run under a different
one without `--force`; and a `no-repro` that contradicts an existing `repro`
for the same issue is worth a warning on its own.

## 10. Don't redirect a script's stdout onto the file the script writes

Pure self-inflicted, but it cost a full 4-minute release sweep:
`python history-2923.py > manual-case-history.txt` — the script writes that
same file itself, so the shell's redirect held it open, the script's own write
failed with `PermissionError`, and what survived was the short progress log
sitting in a filename that promised 300 KB of detail. The summary table was
still there and still correct, which is what makes it dangerous: the artifact
looked plausible.

## 11. Smaller mechanical traps

* **`opt.exe` from this build does not have the PIX passes linked**, even
  though `tools/clang/test/HLSLFileCheck/pix/*.hlsl` invoke them as
  `%opt -S -dxil-annotate-with-virtual-regs`. `-dxil-annotate-with-virtual-regs`
  is simply an unknown option there. `dxopt.exe` has them (it loads
  `dxcompiler.dll`). If you copy a command line out of a lit test, check which
  `opt` the lit substitution actually resolves to.
* **`dxopt` argument order is load-bearing**: `-o=`, `-external`,
  `-external-fn` must all precede the input file, because the parser breaks out
  of the flag loop at the first non-flag operand. Wrong order fails with a bare
  `0x80070057`. `-external <path>` is space-separated; `-external=<path>` is
  not accepted.
* **`dxa -extractpart=dbgmodule` writes bitcode**, not text, despite the help
  text reading like it emits a module. Disassemble with `opt -S`.
* **PowerShell mangles `dxa.exe -extractpart=x -o=y`** into "Too many
  positional arguments"; drive it through `cmd.exe` (this is what
  `run-2923.cmd` is for).
* **`triage.py run`'s capture header hardcodes `$ dxc <args>`** even when the
  compiler is not `dxc`. The `[exe]` / `# exe:` lines are honest, but the `$`
  line reads like a runnable command and is not one. Minor, but it is the line
  a reader's eye lands on first, and I nearly pasted it into the draft comment.

## 12. "The unit test fails" is usually the wrong predicate

Tempting here, since the issue *is* "edit this unit test and it fails". But an
emulated `TestStructAnnotationCase` fails for at least three unrelated reasons:

* the actual bug (writes numbered onto the wrong absolute registers);
* an `inout` variant, which is **not** buggy — it just gives one alloca two
  `dbg.declare`s, so `FindStructMemberFromStore` rejects every store and
  `AllocaWrites` comes back empty;
* plain debug-info shape drift on old releases — the *unmodified control*
  reads "test FAILS" on everything before v1.7.2207.

A predicate that fires on the control is worthless for history work. The one I
settled on — *a source variable is given a virtual-register range that then
receives no writes at all* — is a statement about the data structure being
self-inconsistent, and it fires on the repro at both opt levels and on neither
control at any release. **Prefer a predicate that names the corruption over one
that names a failing assertion**; assertions have many causes.
