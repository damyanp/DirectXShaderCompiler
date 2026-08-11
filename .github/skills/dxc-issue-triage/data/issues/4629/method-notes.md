# Method notes — from triaging #4629

Observations about the *method and tooling*, not about the issue. Recorded because the brief
asks for them and because each one cost time that a future worker need not spend.

---

## 1. `is_internal_failure()` returns True for `timed_out`, which merges a hang into a crash

`triage.py:322`. In general this is right — a compiler that never returns has failed
internally, and you do want the release scan to notice. But on a crash issue it silently
merges two observably different failure modes into one verdict, and the merge is in the
direction that inflates the result: it let a first pass conclude "all 20 releases crash
exactly as reported" when the two oldest do not crash at all, they spin.

This will bite any crash issue whose oldest releases are slow or hung rather than broken, and
nothing in the output flags it. The `repro` verdict looks identical either way; you only see
it if you read the `timed_out: 1` line in the capture, which is easy not to do when 20 rows
all say `repro`.

The remedy is cheap and composes out of predicates that already exist:

```json
{ "kind": "all_of",
  "value": [ { "kind": "internal_failure" },
             { "kind": "timeout", "invert": true } ] }
```

Run the scan under both. If they agree, you have lost nothing and gained a sentence you can
defend. If they disagree, the disagreement is itself the finding. Here it turned
"20 releases crash" into "18 crash exactly as reported, the 2 oldest hang instead", which is
both more accurate and more useful.

**Worth considering for the skill:** `bisect` could warn when a `repro` verdict rests on
`timed_out` — a one-line note in the summary, e.g. `2 of 20 matched via timeout`. That is the
kind of thing a worker cannot notice by inspection but the tool knows for free.

## 2. A control that varies one variable for compiler A can vary *zero* for compiler B

The best mistake of this triage, and the one most likely to recur.

`control-nointerface.hlsl` removes the interface from the derived class's *inheritance list*
while still **declaring** the `interface` block above it. Against DXC that is exactly right:
one variable changes, and the crash goes away. Against Compiler Explorer's `hlsl_clang_trunk`
it is worthless — Clang rejects the `interface` keyword at parse time, so the control fails
for the same reason the subject does and demonstrates nothing.

I only caught it because the control script printed `MIXED` instead of a clean conclusion. The
fix was a second, inline control with the keyword removed *entirely*, which does compile under
Clang; that pins the failure to the keyword rather than to the shader.

The general lesson: **a control is only valid against the compiler it was designed for.**
Reusing local controls in a CE pane, or vice versa, needs re-derivation, not copying. And a
control script should be written so it can *say it failed* — if `verify-clang-control.py` had
just printed its cases without evaluating them, I would have shipped the bad control.

## 3. The feature-absence markers fire on a deliberately-planted typo

I wrote `control-syntaxerror.hlsl` (an undeclared type) to show that an ordinary diagnosed
error is not scored as a crash, declared `--expect no-match`, and got `invalid-probe`:
`unknown type name` is one of the classifier's feature-absence markers — the same string a
release prints when it genuinely lacks a construct.

The classifier is right and my expectation was wrong. There is no way for it to distinguish
"you typed a name that does not exist" from "this compiler does not have that feature yet",
because at the level of the output text those are the same event.

So: **a "plain diagnosed error" control should use a parse error, not an undeclared
identifier.** `control-parseerror.hlsl` (a missing semicolon) yields
`error: expected ';' at end of declaration`, is marker-free, exits `0x80004005` — byte-identical
to the crash path on 14 of 20 releases — and scores `no-repro`. That is the control that
actually does the job.

`triage.py expect` handled the correction properly, leaving the wrong prediction in the record
rather than letting me quietly rewrite it. That is the right design and worth keeping.

## 4. Targeting a reporter's newest flags silently truncates the release history

The reporter filed `-T ps_6_5 -E PSMain -HV 2021`. Run as filed, the four oldest releases
answer `dxc failed : Unknown HLSL version: 2021` at exit 1 — `invalid-probe`. The history would
have started at v1.6.2112 and quietly lost four releases, **including both hangs and the only
access violation**. The scan would not have looked wrong; it would have looked shorter.

Reporters naturally file with whatever they had installed. That is not the same as the flags
the bug needs. Before scanning, it is worth asking which flags are load-bearing and *measuring*
the answer — here, dropping `-HV 2021` and `ps_6_5` changed nothing, confirmed three ways
including byte-identical debugger frame offsets.

The safeguards that made this defensible rather than sloppy: keep the original verbatim in
`cmd-as-filed.txt`, explain the deviation in a comment header inside `cmd.txt` (which supports
`#` lines), and run *both* command lines against every release so no conclusion depends on the
widening holding.

**Worth considering for the skill:** step 3 could say explicitly that an `invalid-probe` run
at the *old end* of a scan is a prompt to re-examine the command line, not just a row to skip.
A cluster of invalid probes at one end is nearly always the harness, not the compiler.

## 5. Check `DXASSERT` against `NDEBUG` before calling a Debug-only assert Debug-only

A Debug build asserting where Release does not *looks* like the assert is over-strict. The
converse is at least as common: `DXASSERT` expands to `do { } while (0)` under `NDEBUG`
(`include/dxc/Support/Global.h`), so the check disappears and whatever it was guarding runs
anyway. Here the very next statement is `cast<IntrinsicInst>(U)` on the value the assert was
checking — i.e. Release does not avoid the bug, it just meets it two lines later and reports
it worse.

Reading the source around the assert takes a minute and is what separates "Debug-only
artefact, low priority" from "same defect, worse diagnostics in Release". Stepping past the
trap in a debugger is even better: the *same binary* then produced the reporter's exact
message and exit code, which ties both signatures to one defect by demonstration rather than
by argument.

## 6. Driving `cdb` from Python: use the verbatim string form

`subprocess.run(['cmd.exe', '/c', '"<quoted exe>" ...'])` fails with *"... is not recognized as
an internal or external command"*, because Python re-quotes the argument list and `cmd.exe`
then strips quotes in its own particular way. The first stack capture came back with **zero
frames and exit 1**, which looks exactly like "the debugger found nothing" rather than "the
command never ran".

What works is passing one verbatim string and letting `cmd.exe` parse it:

```python
subprocess.run('cmd.exe /s /c "' + cmdline + ' 2>&1"', ...)
```

`/s` with the outer quotes is the documented form. **The failure mode is the dangerous part:
an empty capture reads as a negative result.** Any generator script that shells out should
assert it captured something before writing its output file.

## 7. Small API and environment facts

- The real capture API is `triage.read_out(path) -> (meta, body)` and
  `triage._eval_match(m, text, rc, timed_out, path) -> bool`. There is no `read_capture` or
  `evaluate`. Both are worth knowing because they let you **re-score existing captures under a
  different predicate with no compiler run at all** — which is how the predicate-trap
  demonstration was produced, and it takes seconds.
- `releases.cached_path` is the **full path to `dxc.exe`**, not the directory containing it,
  and its shape varies by release: `v1.4.1907\dxc.exe` but `v1.5.2010\bin\x64\dxc.exe`.
  Joining `"dxc.exe"` onto it fails on every row.
- `psutil` is not installed. For CPU-time sampling on Windows, `GetProcessTimes` via `ctypes`
  is stdlib-only, more precise, and avoids adding a dependency to measure something once.
  Launch the process directly rather than through `cmd.exe` so the PID you sample is the
  compiler's and not a shell's.
- `triage.py` lives at `.github/skills/dxc-issue-triage/scripts/triage.py`. Briefs that say
  "`scripts/triage.py`" mean relative to the skill directory, not the repo root.
- The `grep`/ripgrep tooling times out or silently skips dot-directories under `.github/`.
  `Select-String` works.

## 8. Every `.hlsl` in an issue directory needs a tool-made capture

`audit` requires one, which is a good rule — it stops stray files being mistaken for evidence.
The consequence to remember: a helper script that *writes* a shader at runtime (here, a
trivial control for the hang measurement) leaves a `.hlsl` behind that will trip the gate.
Either give it a real capture via `run --shader ... --expect ...`, which is usually the honest
choice since it is a genuine control, or have the script clean up after itself.

Related: scratch files created while investigating by hand (`scratch-*.hlsl`) must be deleted
before the gates run. Worth doing as you go rather than at the end.
