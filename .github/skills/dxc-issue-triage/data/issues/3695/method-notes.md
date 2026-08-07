# Method and tooling observations — #3695

Written per the brief: observations about the *method*, not about the issue. `SKILL.md` and
`scripts/` were not touched.

---

## 1. Compiler Explorer pane text carries ANSI escapes, and a text predicate would not see through them

The most consequential thing I found, and I found it by accident.

`manual-case-godbolt-verify.txt` renders as

```
<source>:84:14: error: assignment to global resource variable '_blurResult' is not allowed
```

but the bytes on disk are

```
\x1b[0m\x1b[1m<source>:84:14: \x1b[0m\x1b[0;1;31merror: \x1b[0m\x1b[1massignment to global resource variable '_blurResult' is not allowed\x1b[0m
```

CE's API returns SGR colour codes inline and `godbolt` stores them verbatim. Two consequences:

- **quoting from the file into a comment silently launders the escapes** (any editor or
  terminal shows the clean text), so a "verbatim" quote cannot be re-verified by substring
  search. `verify-comment.py` failed two checks on text that was demonstrably present, which is
  how I noticed;
- more seriously, **`error:` in that line is `\x1b[0;1;31merror: \x1b[0m`**. A `regex` or
  `stderr_contains` predicate of the form `error:.*not allowed`, or an *absence* predicate like
  `not_regex "error"`, evaluated against CE output would be defeated by a colour code sitting
  between the two halves of the match. This is the same shape as the batch-008 absence-predicate
  hazard, arriving through a different door: the text is there, the match is not.

This triage was not exposed — its predicate is `internal_failure`, which reads exit status. But
any issue whose CE result has to be scored by *text* is. Suggested handling: strip
`\x1b\[[0-9;]*[A-Za-z]` when writing the pane file, or at minimum note in `SKILL.md` that CE
captures are ANSI-coloured and must be de-escaped before any textual comparison.

## 2. `godbolt`'s one-line-per-pane summary hid the headline again — but the full-pane file caught it

Console output was three lines, one per pane, and the Clang pane's first line is an unrelated
`-Qembed_debug` unused-argument warning. The finding that made this triage interesting —
Clang's HLSL front end *diagnoses* this source with a location — is 30 lines further down and
appears nowhere in the summary.

This reproduces the batch-008 lesson exactly. Reporting it as **corroboration that the existing
mitigation works**: `manual-case-godbolt-verify.txt` is written automatically and contained the
finding, so the fix is the right one. What is still missing is any pressure to *open* it. A
one-line hint at the end of the summary — `full pane output: manual-case-godbolt-verify.txt` —
would cost nothing and would close the loop for a worker who does not already know to look.

## 3. `godbolt-note.txt` is `//`-prefixed by the tool, so writing comment markers yourself double-prefixes

`SKILL.md` describes the note as being prepended "as a `// What to look for` banner", which
reads as an instruction to write comment syntax. In fact `annotate()` prefixes **every** line
with `// `, so a note written with markers publishes as `// // What to look for`. I had to
rewrite the note and republish, which burns a shortlink and means the first link
(`bnzP3MqhY`) is now a superseded artifact that must not be cited. Suggested wording: *write
`godbolt-note.txt` as plain prose; the tool adds the comment markers.*

## 4. `run --expect` is a discovery instrument, not just a check

Both minimisation hypotheses I formed from reading the issue were **wrong**, and the thing that
told me so was `WARNING: control expected match but scored no-repro`. I had declared
`minimal-assign.hlsl` (`A = B`, straight from the issue body's own explanation) as `--expect
match`; it is diagnosed, not crashed. Without the declaration the run would have produced a
`no-repro` row I would have read as "not minimal enough" and moved past.

Worth stating positively in `SKILL.md`: **declare an expectation on every variant, especially
ones you are confident about**, because the warning is the only mechanism that converts a
confident wrong belief into a visible event. `triage.py expect` then corrects the declaration
without disturbing the measurement, which is the right separation.

## 5. `match-accepts.json` → `invalid-probe` worked exactly as designed, and made a second bisection unnecessary

The issue makes two claims: it crashes, *and* it should not compile successfully. I wrote a
second predicate for the latter (`nonzero_exit` inverted). On a crashing build `run`
auto-classified it `invalid-probe` and stamped a reason. Correct: a build that died never
answered the question.

The follow-on judgement is worth recording because SKILL's advice ("write a second predicate
and bisect each") does not cover it: **a second predicate that is `invalid-probe` on the ground
truth is `invalid-probe` on every release too, so bisecting it produces 20 rows of nothing.**
The claim it was meant to test is already carried by the 20 nonzero exit codes. I skipped that
bisection deliberately. Suggested addition: bisect a second predicate only after confirming it
is not `invalid-probe` on the ground-truth build.

## 6. A single `cdb` stack can be silently incomplete

The first capture showed frames `00`–`09` ending at `DxilInst_CreateHandleForLib::operator
bool`, then jumped straight to `llvm::legacy::PassManager::run` — the four frames that actually
name the pass were missing, with no gap marker and no warning. A later identical invocation
resolved the full chain including
`DxilLowerCreateHandleForLib::ReplaceResourceUserWithHandle`. The difference is symbol
availability, which varies with what the symbol server has warmed.

Had I stopped at the first dump I would have written "reached from `operator bool`" and been
unable to name the pass — a materially weaker comment, with nothing to indicate anything was
missing. **Take a stack twice, and treat a chain that skips from a leaf helper to
`PassManager::run` as unresolved rather than as a fact.**

A related consequence for reproducibility: because stack addresses (`Child-SP`/`RetAddr`) shift
between runs, a debugger capture is **not** byte-stable, so it cannot be checked by hashing.
Re-running `capture-assert.py` after an unrelated edit changed the file hash while every frame
name and message stayed identical. Verify these artifacts by asserting the symbols and strings
that matter are present, not by diffing the file.

## 11. A committed harness needs a repo-relative default, not just an environment override

`capture-assert.py` and `minimise.py` both took the dxc path from `DXC_TRIAGE_DXC` with a
*fallback* — and the fallback was `<repo>/build/Debug/bin/dxc.exe`, my
machine's checkout location. The override made it feel portable while the default silently
hard-coded one person's directory layout; likewise `cdb.exe` was pinned to one Windows Kits
path. Fixed here by deriving the repo root from `__file__` and falling back to
`shutil.which("cdb.exe")` plus `%ProgramFiles(x86)%`, then re-running both to confirm identical
results.

SKILL.md states the no-absolute-paths rule for the *repro* (`cmd.txt`, `repro.hlsl`). Worth
extending it explicitly to the `manual-case-*` harnesses, which are the artifacts most likely
to be re-run by someone else — and worth a mechanical check, since `Select-String -Pattern
'C:\\'` over the issue directory finds this in seconds and nothing currently prompts anyone to
run it. (One legitimate exception: absolute paths *inside captured output*, e.g. the debugger
printing `C:\...\include\llvm/Support/Casting.h(96)`, are data and must stay verbatim.)

## 7. `triage.py compiler --list` is not a way to list compilers

`--exe` is required, so the natural read-only spelling errors out. The read-only route is
`triage.py sql "SELECT id, exe_path, git_commit, version FROM compilers"`. Also note the column
is `exe_path`, not `exe` — worth spelling out wherever the table is described, since the
"verify your ground truth first" step is the one place a worker needs this and is exactly the
point at which they have not yet learned the schema.

## 8. `audit --issue N` before a verdict exists is weaker than it looks

Run before `verdict.json` is written, `audit` reports "no missing evidence" having exercised
only its pre-verdict checks. That is a genuinely clean result for the state the directory is
in, but it reads like a full pass. Anyone using it as *the* self-check must run it again after
`verdict`, which is what the brief asks for — worth making the two-phase nature explicit in
`SKILL.md` so it is not mistaken for redundancy.

## 9. Bisection-catalog holes should be argued about, not passed over silently

`v1.5.2003` is `bisectable=0` and was not probed. That is correct here — the issue is from
2021-04 and the releases on both sides of it crash — but the *reasoning* only exists because I
wrote it down. A `--linear` scan that silently omits a release leaves a reader unable to tell
whether the gap was considered. Suggested: have `bisect` emit skipped-but-catalogued releases
into the run output, so the write-up has something to answer to.

## 10. Verifying the draft against the artifacts is cheap and caught two real errors

I wrote `verify-comment.py`, which re-checks every quoted string, exit code, shader body and
cited issue number in `comment.md` against the file it came from (39 checks). SKILL.md says
"quote compiler output verbatim and verified, not from memory. Re-run it" — re-running covers
the compiler, but nothing covers the *transcription*, which is the step with no natural check:
a paraphrased error message reads perfectly and is wrong.

It found the ANSI problem in §1, and it enforces things prose review is bad at — that the
inlined HLSL is byte-identical to the committed `minimal-crash.hlsl`, that the superseded
shortlink is absent, that the hex exit codes match the decimal ones in the captures. This
generalises to any issue and might be worth promoting into `scripts/`.
