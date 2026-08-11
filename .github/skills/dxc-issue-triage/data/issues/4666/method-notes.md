# Method notes from issue 4666

Lessons about the *method*, not about this issue. Each one cost a wrong or
nearly-wrong answer here.

---

## 1. When the symptom is a diagnostic, the safety net is off

`classify()` demotes a probe to `invalid-probe` when the output carries a
feature-absence marker — `use of undeclared identifier`, `unknown type name`,
`CodeGen not available`, and so on. That protects against a release which
*could not run* the repro.

It does nothing when the symptom **is** an error message. A release predating the
relevant support emits its own error, which is not in the marker list, and scores
as a textbook reproduction. The output looks entirely healthy. For this issue the
symptom text is `variable has incomplete type`, which is not a marker, so a
construct that had simply never been supported would have been recorded as an
always-reproducing defect with nothing anywhere looking wrong.

**Defence: a per-release positive control that proves the support was present.**
Not "did the compiler run", but "did *this construct* work here". For 4666 that
was `control-struct-first.hlsl` — byte-identical to `repro.hlsl` apart from one
declaration the issue body says suppresses the error. Run it on every probed
release; a release where the control fails is disqualified, not counted.

Corollary: match the **exact** diagnostic text. A predicate that matches "any
error" is what makes this trap fire. `match.json` here pins the full sentence
including the type spelling.

## 2. "The control compiled" is not the same as "the construct was materialised"

A control can pass for the wrong reason. v1.5.2010 ran the SPIR-V control and
exited 0 — but it does not honour `[noinline]`, so it inlined the helper and never
emitted the type the symptom is about. Scoring that as "clean" would have
manufactured a fix boundary out of nothing.

**Defence: assert on the artefact, not the exit code.** The matrix greps the
emitted module for the construct and reports `CONTROL-NOT-MATERIALISED` when it
is absent, which is a third outcome distinct from both clean and reproducing.
Unmeasurable is not the same as clean, and the record has to be able to say so.

## 3. A toolchain component can move underneath you and look like a fix

Symptom B appeared to have a clean v1.6.2104 and a broken v1.6.2106 — a textbook
regression boundary. It was not. v1.6.2104 emits the identical malformed module
and exits 0 because its bundled SPIRV-Tools predates the validation rule. The
defect never moved; the *validator* was upgraded.

Anything DXC ships alongside itself — SPIRV-Tools, DXIL.dll, the validator
version — can produce a boundary that has nothing to do with the compiler.

**Defence: separate "is the bad thing emitted" from "does something complain".**
Add a structural arm that disables validation (`-Vd` here) and matches on the
emitted IR. If the structural arm is flat across a boundary where the diagnostic
arm steps, the boundary belongs to the checker, not the compiler.

Same family: validator wording drifts. `must not contain an opaque type` became
`must not contain an invalid opaque type` at v1.9.2602. A predicate quoting the
current wording would have invented a fix there. `(?:invalid )?` covers it —
and the general rule is to read the old release's actual output before pinning
any wording.

## 4. A reconstruction can be unfaithful in a way that produces silence

The issue body shows a struct passed to a function. The obvious reconstruction —
a plain helper taking that struct — compiles clean on `main` and on every release,
because DXC inlines it and the struct type is never emitted. I had a clean
history for a symptom I had simply failed to reproduce, and nothing about the
output said so; a clean run looks the same whether the bug is absent or the test
is wrong.

**Defence: require a positive identification before believing a clean result.**
The fix was `[noinline]`, and what justified it was that the resulting diagnostic
matched the reported one *including its operand*
(`%Test = OpTypeStruct %_arr_type_sampler_uint_2`). A clean result on a
reconstruction you cannot tie to the report is not evidence of anything. Things
that did *not* reproduce it, and would have been plausible guesses: `-Od`,
`-fcgl`, a global instance of the struct, and a raytracing `lib_6_3` entry.

## 5. Do not merge a second target into `cmd.txt`

Tempting for a two-symptom issue: put the DXIL line and the `-spirv` line in one
`cmd.txt` and let `bisect` cover both. It destroys the older half of the history —
on v1.4.1907 the `SPIR-V CodeGen not available` marker demotes the *whole*
combined capture to `invalid-probe`, taking the perfectly good DXIL measurement
with it.

**Defence: one target per `cmd.txt`.** Secondary symptoms go through labelled
`run --args` variants and an issue-local matrix, which can also run a *different*
shader per release — something `bisect` cannot do, and which the per-release
control in §1 requires.

## 6. Predict before you run — the falsified prediction is the informative one

`--expect` is worth using even when you are confident, precisely because being
wrong is the case that teaches you something. `--expect no-match` on the DXIL
struct workaround returned an internal compiler error instead, which is how an
independent, older, unreported crash was found. Without a recorded prediction
that result reads as one more line of output; with one, it is a surprise that
demands explanation.

What to do with the artefact afterwards is a separate question, and `audit` has
an opinion: a run recorded as a *control* that scores the wrong way is reported
as a failed control, because normally that means the predicate does not
discriminate or the control is not what you thought. Here it meant neither — the
input genuinely crashes. The honest resolution is not to keep an assertion you no
longer believe (that this input should be no-match under the *primary* symptom's
predicate), nor to quietly re-run it into agreement, but to **re-file it under a
predicate that describes what it actually is**: an `internal_failure` probe with
`--expect match`, plus its own scalar control. The falsified prediction survives
where it belongs, in `notes.md`, rather than as a permanently failing control.

## 7. Small mechanical things

- **Nonzero exit is not a crash.** dxc returns `0x80004005` (E_FAIL) for
  ordinary diagnosed errors. Crash-shaped means `0xC0000005`, `0xE0000001`,
  `Internal compiler error`, an assert, or a timeout — and on Compiler Explorer,
  a shell signal code ≥ 128. Use an `internal_failure` predicate for those
  rather than matching message text: the same crash prints
  `Internal compiler error: LLVM Assert` on a Debug build and
  `access violation ... 0x0` on Release, so no text is stable across compilers.
- **Two cache roots, neither a superset.** `.cache/compilers/releases/` and
  `build/tools/clang/test/dxc_releases/`. A release missing from one may be in
  the other.
- **Some old releases reject `--version`** (`Unknown argument`). Record the
  refusal verbatim instead of treating it as a failed probe.
- **`grep`/ripgrep silently returns nothing under `.github/`.** Use
  `Select-String`. A zero-match grep there is not evidence of absence.
- **CE appends `-Zi -Qembed_debug`,** so the `godbolt-note.txt` banner is
  compiled into `!dx.source.contents`. Keep the symptom's literal text out of the
  banner or the predicate can match the banner rather than the compiler's
  behaviour. Describe the symptom structurally — which line, which exit status.
