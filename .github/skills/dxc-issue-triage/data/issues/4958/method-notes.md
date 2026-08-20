# Method notes — #4958

Observations about the *method*, for collation to consider promoting. Nothing here is a
verdict about this issue; that lives in `notes.md` / `verdict.json`.

## `cdb` invocation: the skill's own example `--` separator does not work

`SKILL.md`'s cdb incantations are all written as
`cdb -c "..." <dxc.exe> <args...>` -- and one earlier draft of this section (mine, before
testing it) inserted a literal `--` before the target executable, by analogy with the
`godbolt`/git-style "end of options" convention. That fails hard: both a raw PowerShell/`cmd`
invocation and a Python `subprocess.run([...])` with `--` in the argv list return
`0x80070057` (E_INVALIDARG) with **no debugger output at all** -- cdb never launches the
target. Removing `--` and passing the executable directly after the `-c` argument works
immediately (confirmed via a minimal `cdb -c "q" <dxc.exe> --version`, which produces normal
debugger output). `cdb`'s own command line is `cdb [options] program [arguments]`; there is no
`--` separator in its grammar. Worth a one-line fix in `SKILL.md`'s cdb examples so the next
person does not lose a round-trip to it (I did not have another issue's cdb transcript to
compare against, so I cannot say whether this has bitten anyone before).

## `get_stack.py`-style harnesses need to redact their own compiler path up front

The skill's cdb guidance (and the general "commit the generator next to its output" rule) does
not call out that a small ad hoc Python harness invoking `cdb`/`dxc` directly will, by
default, both hardcode this machine's absolute repo path in its own source (an
`invoke_run --shader/--args` capture never has this problem, because `triage.py run` resolves
the compiler through the registered `compilers` table and calls `display_exe`/`redact_paths`
internally) *and* bake the same absolute path into its captured stdout, since `cdb`'s
`CommandLine:`/`ModLoad:` lines echo whatever path was passed on argv. `check_paths.py` caught
both forms here (`get_stack.py:6` and `manual-case-assert-stack-full.txt` in several places).
The fix used here: resolve the compiler path from `REPO_ROOT` (imported from `scripts/triage`)
instead of a literal string, and pipe all captured text through `triage.py`'s own
`redact_paths` before writing -- both are already public functions in `triage.py`, just never
imported from an issue-local harness before. Reusing them rather than reinventing a
prefix-strip is what made the redaction agree byte-for-byte with the convention every other
captured file in this tree already uses (`<repo>/...`). Might be worth exposing this as an
explicit "use `triage.redact_paths` in any custom harness" line in the `cdb` section of
`SKILL.md`, next to the existing custom-harness guidance for `IDxcOptimizer`-style passes.

## `run --shader` retargeting a `#define`-parameterised repro

The reporter's repro hardcodes `ARRAY_SIZE` via `#define`, and the reported symptom's shape
(crash vs. clean) is claimed to depend on that value. `run --shader <file> --label <name>
--hypothesis --expect <match|no-match>` handled this cleanly by treating each `ARRAY_SIZE`
value as its own small variant file (a copy of `repro.hlsl` with one line edited), rather than
trying to pass `-D ARRAY_SIZE=N` on the command line -- the source already `#define`s the same
name, so a command-line `-D` would just redefine-and-warn instead of taking effect, and
silently produce a false "the value did not matter" reading if not checked. Not a tooling gap,
just a trap worth flagging: **when a repro's own source `#define`s the parameter under test,
don't reach for `-D` to vary it** -- make a variant file instead, same as any other control.
