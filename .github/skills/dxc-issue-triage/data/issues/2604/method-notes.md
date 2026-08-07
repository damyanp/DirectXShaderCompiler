# Method notes from #2604

Things learned about the *method* and the tooling, for promotion into
SKILL.md at collation. Concrete, with what happened.

---

## 1. A control can rescue you from a status code that means two things

The strongest thing that happened in this triage. The SPIR-V probe asks
"does `-Fc` work through the API when `-spirv` is on?" On v1.4.1907 and
v1.5.2003 it returns `0x80070057` — the *identical* status to the `-Fc`
rejection on every other release. The obvious reading, "SPIR-V rejects `-Fc`
too, on all 21 releases", is **wrong**: those two DLLs were built without
SPIR-V, and the error text is

    SPIR-V CodeGen not available. Please recompile with -DENABLE_SPIRV_CODEGEN=ON.

Only a *baseline* case — compile with `-spirv` and **no** `-Fc` first, require
it to succeed and produce an object, and skip the `-Fc` cases if it doesn't —
separates the two. The harness does that and reports those rows as `no-spirv`.

The general rule, worth stating in SKILL.md: **when a probe adds a feature
flag, that flag needs its own baseline.** An error code tells you something
failed, never what. If the same code can arise from "the feature under test is
missing" and "the flag that enables the whole path is missing", a probe without
a flag-enabled baseline is measuring an ambiguity and reporting a fact.

The generalisation of the existing "anchor the absence" rule is: anchor each
*axis* separately. This probe needed three anchors, not one — compile works
(`c1-baseline`), disassembly is obtainable (`c1-disassemble`), and the SPIR-V
path works (`c1-spirv-baseline`). Each rules out a different way of being
vacuously true.

## 2. The `invalid-probe` classifier can collide with the symptom itself

`triage.py` treats `Unknown argument` in output as a feature-absence marker
and demotes a non-matching run to `invalid-probe`. For this issue the symptom
*is* that string, so the `-Fh` control — a legitimate contrast, `-Fh` being
the only other `DriverOption`-only `-F*` option — could not be declared
`--expect no-match`. It is `--expect invalid-probe`, which is honest but reads
oddly in the capture list without explanation.

(Matching probes are not demoted, so the primary captures were unaffected.
The header now carries an `# invalid-probe-reason:` line, which is good and
made this diagnosable in one read.)

SKILL.md should say: **when the issue's symptom text is one of the
feature-absence markers, expect controls to score `invalid-probe` rather than
`no-match`, declare that explicitly with `--expect invalid-probe`, and say why
in `notes.md`.** Otherwise a reviewer sees an `invalid-probe` in the control
table and reasonably assumes the probe is broken.

## 3. Don't bisect an API issue with the driver — a third instance

Recorded on #2923 and #3237; hit again here, and this one is the sharpest
case yet because the wrong answer is *maximally* confident. `triage.py bisect`
resolves each tag to that release's `dxc.exe` and drives it with `cmd.txt`.
For #2604 `dxc.exe` is the *only* caller that handles `-Fc`, so a bisect would
score all 21 releases `no-repro` and print "never repro'd in releases" for a
behaviour that has never once worked.

Three issues in a row suggests this deserves a hard gate rather than a note:
**if the issue is about `IDxc*` behaviour, `bisect` is not applicable — write
a release matrix that swaps `dxcompiler.dll` instead.** A one-line check in
`bisect` — "this issue's registered compiler is a harness, refuse and point at
the matrix pattern" — would remove the trap entirely.

## 4. Re-run *every* capture after touching the harness, not just the failing one

Mid-triage I changed `ReadOutputs` to handle DLLs with no `IDxcResult` (pre
DXC 1.6), and later added three SPIR-V cases. Both times, captures already on
disk had been produced by the previous binary. They still *looked* fine —
same verdicts, plausible content — and nothing in the tooling flags a capture
as stale relative to the harness that produced it.

Practice that worked: after any harness edit, rebuild and re-run **all**
captures (primaries with `--force`, then every `--label` variant), before
writing anything up. Note `--force` is needed even for a re-run of the same
predicate, and that the refusal message is good — it names the old predicate
and the new one.

SKILL.md could go further: a capture header records `# ran:` but not a hash of
the harness binary. **Recording the harness's `--version` line (or an mtime)
in the capture header would make staleness detectable** instead of relying on
the agent's memory.

## 5. `--match` paths are resolved relative to the issue directory

`--match data\issues\2604\match-einvalidarg.json` produced a spurious
"refusing to overwrite … it was captured under `match-einvalidarg.json`, this
run scores `data\issues\2604\match-einvalidarg.json`" — the same file by two
spellings, treated as two predicates. `--match match-einvalidarg.json` (bare
filename) is correct. Cheap fix: normalise the path before comparing.

## 6. `run --label` requires `--shader` or `--args`

`--label` alone with a different `--compiler` is rejected. To capture "the
same command line through `dxc.exe`" you must re-state the arguments:

    triage.py run --issue 2604 --compiler main-debug --label cmdline \
        --args "-T ps_6_0 -E main -Fc repro-fc.asm repro.hlsl"

That is a *restatement of `cmd.txt`* typed by hand into a shell — precisely
the transcription that the "echo the command you ran" rule exists to prevent
elsewhere. Worth either allowing `--label` with an unchanged command line, or
warning in SKILL.md that this one place requires manual duplication and the
two should be diffed.

## 7. A capture can be empty and still be the whole point

`variant-cmdline-main-debug.txt` records `dxc.exe` succeeding: exit 0, no
output. Read alone it looks like nothing happened. The entire effect of `-Fc`
is a *file*, and a file is in nobody's stdout.

**When the behaviour under test is a side effect on the filesystem, the
capture cannot carry the evidence — a `manual-case-*.txt` that stats and
excerpts the file must.** Generalises to `-Fo`, `-Fh`, `-Fd`, `-Fre`, `-Frs`,
`-Fsh`, `-Fi` and anything else whose output is a path.

## 8. Verify prose facts about the issue thread against `issue.json`

I wrote a draft sentence crediting the 2020 comment to a named user. The
`author.login` for that comment is the **empty string** — a deleted account —
confirmed both in `issue.json` and via `gh issue view --json comments`. The
name was invented by me from nothing, in a file destined for a public comment.

**Any `@mention` in `comment.md` must be checked against `issue.json` before
the draft is considered done**, and an empty login means refer to the comment
by date, never by a guessed handle. The existing evidence rule covers compiler
behaviour; it should cover claims about the thread too.

## 9. Check the documentation the reporter cites — as a measurement

I initially reasoned that the 2020 commenter had over-read
`docs/SPIR-V.rst` ("the sentence is scoped to the SPIR-V list that follows,
which does not include `-Fc`"). That was wrong, and I only found out by
grepping instead of reasoning: line 4211 of that list *is*
"``-Fc``: outputs SPIR-V disassembly to the given file". The doc says exactly
what the reporter said it says.

That turned a dismissive paragraph into a real, separable, actionable finding
— and it changed the probe design (the SPIR-V cases exist because of it).
**When an issue cites documentation, open the documentation, and if it makes a
behavioural claim, measure the claim.** Docs are a testable artifact.

Related trap, since it's what nearly hid this: `Select-String -Pattern 'a|b'
-SimpleMatch` treats the whole alternation as one literal and silently finds
nothing. Validating against a known positive (`-Pattern 'SPIR-V'` → 251 hits)
is what exposed it.

## 10. `git log -L <line>,<line>:<file>` is the cheapest "has this ever changed"

One command, one answer:

    git log -L 505,505:include/dxc/Support/HLSLOptions.td --format='%h %ad %s' --date=short -s
    -> 6ee4074a4 2016-12-28 first commit

It follows the line through renames and reindents, so a single result really
does mean "one state, ever". Far stronger and cheaper than `git log -S` over a
whole file, which reports commits that merely touch the string elsewhere.
Multiple `-L` ranges can be combined in one invocation (used for the two
`docs/SPIR-V.rst` lines). This belongs in SKILL.md's history section next to
`bisect`, as the *source-side* history check — it answers "was this ever
different?" without building anything.

## 11. Make source claims re-runnable, with controls, in a file

`manual-case-source-evidence.txt` is generated by `measure-2604.py --source`:
each claim is a `git grep`/`git log` echoed and executed, and the two
**absence** claims each run a known-positive control first, in the same file,
with the same tool.

That last part matters more than it sounds. `notes.md` asserts "`AssemblyCode`
has no reader inside `dxcompiler/`". On its own that is a claim about a
command nobody re-ran. With the control immediately above it — same pattern,
repo-wide, 10 hits — an empty result is evidence rather than an assertion. It
also survives the agent-`grep`-false-zero hazard structurally rather than by
remembering to avoid a tool.

Recommendation: **SKILL.md should ask for a `manual-case-source-evidence.txt`
whenever `notes.md` makes a source-level claim, with the rule that every
absence claim carries a known-positive control in the same file.**

## 12. Two writers, two redactors

`triage.py` redacts paths only in captures *it* writes. A harness's stdout and
a `measure-*.py`'s output both pass through untouched. Both therefore need
their own `Redact()`/`redact()` deriving roots from their own location
(`__file__`, `GetModuleFileName`) — never a hardcoded root, and never a token
baked into an executable file, which makes it non-runnable rather than
portable. Confirmed by grepping the finished artifacts for the machine path
and finding none. Already implied by #3237; worth stating as a rule because
there are now three writers in a typical harness triage.
