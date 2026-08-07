# Method / tooling observations from triaging #3377

Observations about the METHOD and the TOOLING, not about the issue. Recorded here for
collation; SKILL.md and scripts/ deliberately untouched.

---

## 1. A text-based crash predicate would have produced a false "fixed" verdict here — with numbers

SKILL.md already says to use `internal_failure` for anything crash-shaped. This issue is a
quantified example of what the rule buys, which may be worth citing in the rule itself.

Of the 20 release binaries probed, **8 crash with completely empty stderr**: v1.4.1907,
v1.5.2010, v1.7.2308, v1.8.2405, v1.8.2502, v1.8.2505, v1.8.2505.1, v1.9.2602. Not "a different
message" — no output at all. Any predicate keyed on `Internal compiler error`, on the assert
text, or on `access violation` scores those 8 `no-repro` and invents a fix boundary in the
middle of a uniformly broken history.

Worse, it is not even stable per binary. `manual-case-crash-form.txt` runs each build 10 times:
**v1.8.2502 is silent `0xC0000409` on 7 runs and `0xC0000005` with a message on the other 3.**
The same binary, the same input, a different observable. A text predicate applied to that
release is a coin flip.

## 2. `--repeat` is aimed at *nondeterministic occurrence*, and the docs could say so

The heuristic in SKILL.md is "reach for `--repeat` if the reporter says intermittent, or names
heap corruption / uninitialised memory / ASLR / threading". This issue names heap corruption and
its crash *form* is genuinely heap-layout dependent (§1), so the heuristic fires — but repeating
the scan would have bought nothing, because the *occurrence* is 100%: 40/40 hand runs, 20/20
release probes, 5/5 variant probes.

The distinction that matters is: `--repeat` protects against an unlucky probe **creating a
boundary**. If no probe in the scan scores clean, there is no boundary to be an artefact and
`--repeat` cannot change the answer. Suggested sharpening: reach for `--repeat` when the symptom
is nondeterministic **and** the scan produced a transition; when a scan is uniform in one
direction, measure the hit rate on a few builds instead (cheaper, and it is the number you
actually want to quote).

## 3. `cdb` driven from PowerShell silently produces nothing

Reproducible trap, cost ~20 minutes:

- `cdb -c "..." -- dxc.exe args` invoked **from PowerShell** exits with no output at all. No
  error, no partial transcript, exit 0.
- Same command with multiple `;`-chained commands in `-c` — also empty.
- The `--` argument separator is part of it: cdb does not want it here.

What works is going through `cmd.exe` and redirecting *inside* it, with no `--`:

```powershell
& $env:ComSpec /c '.\assert-stack.cmd > raw.txt 2>&1'
```

Related: `sxe -c "gh" e0000001` inside a `-c` string fails with `Quotes required in ...` when
passed through PowerShell — the nested quotes do not survive. Putting the cdb invocation in a
`.cmd` file and running the file avoids the whole class of problem, and has the side benefit
that the harness is committed and re-runnable, which SKILL.md wants anyway.

## 4. A `.cmd` harness cannot reliably report `ERRORLEVEL`

Tried to write `crash-form.cmd` to run dxc N times and tally exit codes. Two independent ways
it silently lies:

- `set /a HEX=!ERRORLEVEL!` **resets `ERRORLEVEL` itself** before you can use it again.
- A nested `for /f ... powershell ...` to format the value spawns a subprocess that clobbers it.

Both produce plausible-looking output that is wrong. Rewrote as `crash-form.py`
(`subprocess.run(...).returncode`), which is also easier to read. Suggested guidance: **capture
exit statuses from Python, never from `cmd`**, whenever a harness loops.

## 5. Compiler Explorer returns ANSI escape codes in compiler output

CE's compile API returns clang/dxc diagnostics with SGR colour escapes embedded. A
`Select-String 'error:'` over that output returned **0 matches** while the same text was plainly
visible in the transcript — the escape sequence sits between the token boundaries the pattern
assumed.

SKILL.md correctly says ESC bytes in a capture are legitimate and must not be "cleaned" out of
the evidence. The complementary point for the *analysis* step: strip them in the matcher, not in
the file — `re.sub(r'\x1b\[[0-9;]*m', '', text)` before counting or asserting. I got a wrong
count first and only caught it by eyeballing the raw output.

## 6. `triage.py sql` — the compilers table column is `exe_path`, not `exe`

`SELECT id, exe FROM compilers` fails with a no-such-column error. Minor, but the obvious guess
is wrong and the error does not suggest the right name. A `--schema` flag, or naming the columns
in the `sql` subcommand's help, would save a round trip.

## 7. Godbolt shortlinks are verifiable read-only, and that is worth doing routinely

`https://godbolt.org/api/shortlinkinfo/<id>` returns the full session JSON — source, compiler
ids, per-pane options — as a plain GET.

Two uses in this issue, both load-bearing:

- Resolved @llvm-beanz's 2023 link from the thread and **confirmed the flags he used**
  (`-T ps_6_0 -E main_fragment`), which independently corroborated the profile/entry point I had
  inferred from the body rather than leaving it a guess.
- Verified my own published link actually contains the banner, the repro and the intended
  per-pane options — rather than trusting that `triage.py godbolt` published what I passed it.

Suggested as a standard step 7 check: after publishing, GET the shortlinkinfo and diff it
against what you intended.

## 8. `triage.py godbolt` only reports each pane's first output line

Enough to see `SIGSEGV`, not enough to answer "how many errors did clang emit" or "did FXC
actually succeed". Wrote `ce-probe.py` to POST CE's `/api/compiler/<id>/compile` directly and
capture the full stdout/stderr/exit for a chosen compiler, options and source file.

This is what made the FXC and clang comparisons possible at all — and both changed the write-up:
FXC verified the issue body's opening claim, and clang's 13 unrelated parse errors are the reason
the published link has **no** clang pane. Something like `ce-probe.py` may be worth promoting
into `scripts/`.

## 9. Deciding *not* to publish a pane still needs captured evidence

SKILL.md says a missing clang repro beats a noisy useless one. Applying that leaves a gap: the
reasoning for the omission lives nowhere, and a reviewer sees only an absent pane.

Captured it as `manual-case-ce-clang.txt` instead — the 13 errors that disqualify the repro, plus
the two controls showing the harness works (`control-hello.hlsl` exits 0; `variant-no-uniform.hlsl`
exits 0, which is itself the finding that clang has no rule against the construct). Suggested
convention: **when you omit a pane, capture why.** A negative decision is a claim like any other.

## 10. `audit --issue N` is safe; the batch brief's blanket "do not run audit" is broader than needed

The standing instruction is not to run `reindex` or `audit` because they rebuild global state
while other workers are mid-write. That is exactly right for `reindex` and for a bare `audit`.
But `audit --issue 3377` is read-only and single-issue, and it is the only cheap way to check
your own evidence is complete before recording a verdict (it reported `no missing evidence in 1
issue(s)` here). Worth making the carve-out explicit in the batch brief so workers do not skip a
useful self-check.

## 11. Ground-truth verification by tree (already in SKILL.md — confirming it works)

Not a new observation: SKILL.md already carries the "verify by tree, not by SHA" guidance. Noting
only that it was needed and worked here, since a second independent datapoint is cheap.

`main-debug` reports `ab5400907`; repo HEAD had moved to `e86a0fdab`.
`git diff --name-only ab5400907 HEAD` filtered to exclude `.github/skills/dxc-issue-triage/*`
returned **zero files** — every intervening commit was triage-harness churn from parallel workers,
so no compiler source differs and the build is valid ground truth for `main`. No rebuild needed.

This will be the common case in any parallel batch: peers commit into `.github/skills/`
continuously, so HEAD drifts from the build SHA within minutes for reasons that cannot affect the
compiler. Worth keeping the exclusion list narrow — anything outside `.github/` should still force
a rebuild.
