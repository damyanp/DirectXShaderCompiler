# Method notes — from triaging #3906

Observations about the method and the tooling, not about the issue. #3906's own findings are in
`notes.md`.

## 1. The two-signature hazard is real, and `any_of[timeout, internal_failure]` caught it

Confirmed, not merely anticipated. #3906 is a reported hang. Every one of the 20 stable releases
times out on the repro. The **Debug ground truth does not time out** — it exits `0xE0000001` in
about a second on an assert. Scored with a bare `timeout` predicate, `main-debug` would have read
`no-repro` against 20 timing-out releases, and an open, always-reproducing five-year-old bug
would have been written up as **fixed**, with a clean bisect apparently supporting it.

Suggested rule, stronger than the current phrasing: **for any issue whose report describes a hang
or non-termination, `any_of[timeout, internal_failure]` is the default predicate**, pre-registered
in `expected.md`, unless there is a specific reason it is wrong. The cost of the extra arm when it
is unnecessary is zero; the cost of omitting it is a false `close-fixed`.

The same reasoning applies in reverse and is worth stating: a Debug ground truth that *asserts*
where releases *hang* is not a discrepancy to be explained away, it is the expected shape, and the
work is to prove the two are one defect rather than to pick one.

## 2. Proving "Debug assert == Release hang" — the `gh` continuation

The proof that made this issue solid, worth reusing:

1. `cdb -c "sxe -c \"kb 1; gh\" e0000001; g; q"` — break on the assert, print one frame, then
   **`gh` ("go handled")** to continue past it. Continuing past an assert is a decent emulation of
   what a Release build does, since the assert is not compiled in there.
2. That reached a *second* assert whose message literally names the reported symptom.
3. Read the source at both sites and check the `NDEBUG` expansions (`assert` → nothing;
   `DXASSERT_LOCALVAR` → `do { (void)(local); } while (0)` in `include/dxc/Support/Global.h`),
   showing the bail-out's bare `return;` survives while both guards vanish.

That is source-level proof rather than "the Debug build fails and the Release build hangs, so
presumably…". It cost about ten minutes and turned a hedge into a statement.

## 3. Independent evidence that a hang is a spin, not a deadlock: sample CPU time

A timeout says only that the process did not finish. Sampling the child's kernel+user CPU
through `GetProcessTimes` separates a busy loop from a deadlock or an I/O wait — two quite
different bugs with the same wall-clock signature. On #3906 (`manual-case-cpu-sample.txt`):

```
  elapsed     cpu    cpu/elapsed
    15.0s    14.9s    1.00
    ...
    90.0s    89.6s    1.00
```

`cpu/elapsed == 1.00` throughout: a spin. It costs one extra sampling loop (~40 lines of
dependency-free `ctypes` in `make-manual-cases.py`, reusable as-is) and it converts "it did not
finish in the time we gave it" into "it is executing instructions and making no progress". Worth
adding to the method as a standard step for any hang.

Note the discipline point: I first observed this live with `Get-Process dxc | Select CPU` while
the 600 s run was in flight. That is a real observation but it is not re-derivable by a reader
after the process is gone, so it does not meet "evidence or it didn't happen". Folding it into
the generator as a `cpu` case cost 90 s and made it a committed artifact. **If a claim in the
write-up rests on something you watched rather than something you captured, capture it.**

## 4. `triage.py`'s 60 s `TIMEOUT` is a hard-coded module constant with no override

Line 64. There is no `--timeout` flag on `run` or `bisect`. Consequences:

- Every probe is bounded, which is right, but a 60 s timeout cannot distinguish an infinite loop
  from a slow compile, so any hang issue needs a separate hand-rolled long-bound manual case
  (here `make-manual-cases.py hang --seconds 600`). That is boilerplate every hang triage will
  re-invent.
- Bisecting a hang is *slow*: 21 probes × 60 s ≈ 21 minutes of pure waiting for
  `bisect --linear`.

A `--timeout` flag would fix the first. For the second, when both the oldest and the newest
release reproduce, the 18 probes in between establish nothing the endpoints do not — they are
confirmation, not search. If the history field can tolerate "oldest and newest both repro", a
`--endpoints-first` mode would cut a hang bisect from 21 minutes to 2. (Recorded as a suggestion,
not applied — the full scan was run.)

## 5. `cmd /s /c "<one string>"` when driving `cdb` from Python

`subprocess.run([comspec, "/c", subprocess.list2cmdline(argv)])` **mangles the quoted `cdb.exe`
path** and answers:

```
'"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"' is not recognized as an
internal or external command
```

which reads exactly like a missing debugger and sent me looking for one that was installed all
along. `cmd.exe` strips the first and last quote of the command string under `/c`, wrecking a
command that legitimately begins with a quoted path. The fix is to build **one** string and use
`/s`, which makes the stripping rule "remove exactly the outer pair":

```python
subprocess.run(f'{comspec} /s /c "{subprocess.list2cmdline(argv)}"', shell=False)
```

## 6. Never guess a cached release's executable path — read `releases.cached_path`

Downloaded releases sit under **two different on-disk layouts**:

- `<cache>/compilers/releases/<tag>/bin/x64/dxc.exe`
- `<cache>/.../<tag>/dxc_<date>/bin/x64/dxc.exe`

A helper that pattern-builds the first form silently finds nothing for releases in the second.
`triage.db`'s `releases.cached_path` has the answer. An issue-local script should open the DB
read-only (`sqlite3.connect("file:...?mode=ro", uri=True)`) so it cannot write shared state that
other concurrent workers depend on.

## 7. `triage.py sql` column names differ from the obvious guesses

- `runs` has **`compiler`**, not `compiler_id`.
- `compilers` has **`exe_path`**, not `exe`.

Both produce `sqlite3.OperationalError: no such column`, which is at least loud. A
`triage.py sql --schema` shortcut (or printing the table list on error) would save a round trip;
`SELECT name FROM pragma_table_info('runs')` works in the meantime.

## 8. `audit --issue N` passes on an issue with no verdict at all

Run before `verdict.json` existed, `audit --issue 3906` printed `no missing evidence in 1
issue(s)` and exited 0. It checks that the evidence on disk is *coherent*, not that the issue was
*triaged*. That is a reasonable design, but it means audit cannot be used to confirm a worker
finished, and a worker who runs audit as their last step can pass it having recorded nothing.
Reporting "verdict.json missing" as a gap would close that hole at no cost.

## 9. Reporter-stated "necessary conditions" are hypotheses — test them, and expect to be wrong

The report named three conditions and said removing any one avoids the hang. That is an excellent
control suite: three `--expect no-match` controls on the exact axis the report names, much
stronger than a generic hello-world control. **Two of the three predictions were falsified** —
the variants still hung, on the release nearest the report as well as on current builds.

Two process points:

- The workflow of declaring `--expect` *before* running and then correcting with
  `triage.py expect --why "..."` worked exactly as intended: the falsified prediction is on disk
  with its reason, rather than being quietly reconciled. That is the whole value of
  pre-registration and it should keep being enforced.
- The write-up needs care. A reporter's reduction hypothesis failing to hold is a fact about the
  compiler, not about the reporter, and the draft must describe the measured configurations and
  stop. Also: their compiler version is usually unrecoverable and their variants are not yours,
  so "they were wrong" is not supportable even when the measurement is clean. I chose **not** to
  set `text_stale` for this reason — the symptom, repro and workaround are all still accurate,
  and only a reduction hypothesis is in question. Suggest the skill say this explicitly: a
  falsified *reduction claim* is not text staleness.

## 10. Third-party repro hosts die; a Compiler Explorer link is the durable substitute

#3906's only record of the command line was a `shader-playground.timjones.io` permalink, and the
host no longer resolves (DNS failure). The exact arguments are gone. This is a concrete,
non-hypothetical argument for the skill's CE step: attaching `godbolt.org/z/...` gives the issue
a runnable reproduction that outlives its original hosting, and it is worth saying so in the
draft when the original link is dead.

## 11. `grep`/ripgrep silently returns zero matches under `.github/`

The agent's `grep` tool finds nothing anywhere beneath `.github/`, with no error — presumably a
hidden-directory default. It looks identical to "the string is not there", which is a dangerous
failure mode when the conclusion being drawn is a negative. `Select-String` was used throughout
instead, as SKILL.md already advises; the note here is that the failure is *silent*, which is
what makes it worth a warning rather than a preference.

## 12. Path-hygiene gate: this directory is clean by construction, and needs no allowlist entry

`scripts/check_paths.py` was run against the whole tree and passed; separately, its own
`find_hits` regex was run over **only** `data/issues/3906` (56 text files, including ones the
gate skips) and returned **0 hits**. No `ALLOWLIST` entry is needed for anything under 3906.

That is not luck, and the mechanism is worth reusing: every artifact here is generated by
something that redacts before writing. `triage.py`'s `display_exe` tokenises the scored
`out-*.txt` and `variant-*.txt` captures, and `make-manual-cases.py` has a `tokenise()` that
rewrites the three machine roots to `<cache>`, `<triage>` and `<repo>` on the way into every
`manual-case-*.txt` — with those roots *derived* from `__file__`, never spelled out. The prose
files were written with `<repo>\...` from the start. **Redact in the generator, not in the
output**: hand-editing a capture to satisfy the gate would break the guarantee that re-running
the script reproduces what is on disk, which is the whole point of committing the script.

One thing that is *not* a leak and should not be "fixed" by a later pass: the `cdb` invocations
in `manual-case-assert-stack.txt` and `manual-case-assert-identity.txt`, and the quoted `cmd /c`
error message in item 5 above, contain an absolute path to the Windows SDK debugger under
Program Files. The gate rejects only the checkout root and the user-profile root; a Program
Files path is one of `validate_matcher`'s explicit *negative* controls. It is a system location
rather than a contributor's layout, and the command line is evidence — rewriting it would make
the transcript stop being the command that ran.

## 13. Cross-issue observations (kept out of the draft, per the rules)

- The two-signature case documented in SKILL.md is the same shape as #3906 and is now
  corroborated by a second independent measurement. If a third turns up, the guidance should be
  promoted from "consider" to "default for hang reports".
- #3906's mechanism is in `SROA_Parameter_HLSL` / `SROA_Helper`, a DXC-specific pass with no
  counterpart in the Clang-based HLSL front end, which compiles every one of the eight shaders
  cleanly. Any other issue whose stack passes through `RewriteForScalarRepl` or `RewriteBitCast`
  is worth checking for the same `!SrcTy->isStructTy()` / `!DstTy->isStructTy()` bail-outs — both
  return without eliminating the use, and the second one was reachable here too, from a
  one-token change to the repro. Whether those issues are the *same* issue is collation's call,
  not mine.
