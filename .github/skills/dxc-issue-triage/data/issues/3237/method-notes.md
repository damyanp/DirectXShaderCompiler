# Method notes from #3237

Observations about the workflow and tooling, not about the issue. #3237 was
put in this batch as a stress test of the method — the defect is an API return
value, and `dxc.exe` cannot see it — so these are mostly about **where the
tooling ran out**.

## 1. `cmd.txt` + `match.json` cannot express an API return value at all

This is the structural gap. The whole capture format assumes the observable is
text on a compiler's stdout/stderr. When the defect is "this COM method returns
the wrong `HRESULT`", there is nothing to match against until someone writes a
program that calls the method and prints the result — and at that point the
predicate is really matching *the harness's* transcript, one step removed from
the defect.

That indirection is manageable but has to be designed for, not discovered.
Two things made it safe here and would be worth doing every time:

- **The transcript is printed by the same program that made the call**, so
  there is no parsing of someone else's format in between.
- **The harness refuses to print its `RESULT:` line unless the whole walk
  completed**, and prints a loud `WALK-INCOMPLETE: <reason>` instead. Without
  that, "the API returned E_FAIL" and "the harness never got far enough to ask"
  are the same empty output, and the predicate cannot tell them apart. This is
  the #2923 lesson (a control cannot catch a reader that returns *nothing here*
  and *nothing matched* through the same channel) applied at the source.

`not-compiler-verifiable` would have been an honest verdict here. It would also
have been wrong, and about two hours of harness-writing separated the two. The
useful generalisation: **before reaching for `not-compiler-verifiable`, ask
where the code under test physically lives.** It lived in `dxcompiler.dll`,
which every release ships, so it was reachable — the CLI was the obstacle, not
the code.

## 2. `bisect` still cannot drive a harness-as-compiler — third occurrence

`triage.py bisect` builds its command from `cmd.txt` and resolves each release
tag through `ensure_release(tag)` to **that release's `dxc.exe`**. A compiler
registered in the `compilers` table is only honoured for `run --compiler`, not
for the release sweep. So any issue whose repro is not a single `dxc.exe`
invocation has to hand-roll a `measure.py`.

That is now #2918, #2922, #2923 and #3237. The failure mode is worse than
"unsupported": running `bisect` anyway **succeeds**, scores every release
`no-repro`, and reports a confident *never repro'd in releases* — the exact
opposite of the truth, in a format indistinguishable from a real result. Here
the correct history was *always repro'd, 21/21 releases*.

Concrete suggestion, since this keeps recurring: let `bisect` accept a
registered compiler template, e.g. a `--per-release-compiler <cmd>` where the
tag's install directory is substituted, so the sweep can drive something other
than `dxc.exe`. Failing that, `bisect` could refuse to run when the issue
directory contains a `measure.py`, or when the issue's primary capture came
from a compiler that is not `dxc.exe`-shaped — a wrong answer that looks right
is worth more guardrail than an unsupported case.

I deliberately did not work around this by registering compilers named after
release tags (`v1.9.2607` etc.), which *would* make `bisect` work, because
`resolve_compiler` checks the `compilers` table first: those rows are shared
state and would silently redirect every other issue's release probes to my
harness. Worth stating explicitly in SKILL.md as a trap, because it is an
attractive-looking fix.

## 3. A batch-file trap that fails **silently with exit 0**

`%ProgramFiles(x86)%` expands to a string containing a literal `)`. Inside a
`for /f (...)` or `if (...)` block, that close paren **terminates the block
early**. The block then half-executes and the script **still reports exit 0**,
so the failure presents as success. What I actually saw was
`'vswhere.exe' is not recognized` followed by a *successful* build — which
invites you to dismiss the message as noise.

Compounding it: on this machine `vcvars64.bat` itself emits
`'vswhere.exe' is not recognized` as harmless internal noise while working
correctly. So that string is not a usable failure signal in either direction.

Fix used in `build-refl3237.cmd`: no parenthesised blocks anywhere — `goto`
flow with a `:try` subroutine over known VS install paths. Cost about four
rebuild cycles to find. Anything in the skill that writes `.cmd` helpers should
avoid `for`/`if` blocks around paths containing `%ProgramFiles(x86)%`.

## 4. Chase `invalid-probe` rows; do not just exclude them

`v1.4.1907` first came back `invalid-probe` with `IDxcCompiler::Compile call
failed`, which reads like "old release, doesn't support the feature" — and
excluding it would have been easy and quiet. It was actually
`E_INVALIDARG` because that release rejects a null `pEntryPoint` even for a
`lib_*` profile where the value is ignored. One-line fix, and it extended the
history by two releases back to the bisection floor.

The generalisable bit is a diagnostic one: my `Incomplete()` helper originally
**discarded the HRESULT**, printing only a prose reason. That turned a
one-command diagnosis into a round trip. Any harness that aborts a walk should
carry the numeric status into the abort message; I added an overload for this
after being bitten.

## 5. `dxa -dumpreflection` is a useful, partial, unshipped second witness

`dxa -dumpreflection` (`tools/clang/tools/dxa`, backed by
`lib/DxilContainer/D3DReflectionDumper.cpp`) drives `ID3D12LibraryReflection`
and shares no code with a hand-written harness, which makes it an excellent
independent check that a vtable walk landed correctly. Worth remembering for
any future reflection issue.

Two limits: it only prints what the dumper chooses to print (it never calls
`GetFunctionParameter`, so it could corroborate `FunctionParameterCount` but
not the reported `E_FAIL`), and **no release package ships `dxa.exe`** — I
checked all 17 cached release trees. It is a ground-truth-only tool. Every
release *does* ship `dxcompiler.dll`, which is why the per-release harness
works where `dxa` would not.

## 6. `--expect` vocabulary differs from the verdict vocabulary

`run --expect` takes `match` / `no-match` / `invalid-probe`, but the verdicts
it prints are `repro` / `no-repro`. Passing `--expect no-repro` is an
argparse error. Minor, but it cost a round trip on five control runs; the
values would read better if they matched, or if the error message named the
mapping.

## 7. `run --shader` and `--args` do not compose

`--shader X --args "-T cs_6_0"` fails with `no source file to replace in:
-T cs_6_0`: `--args` replaces the whole command line, so the source file has to
be repeated inside it (`--args "-T cs_6_0 -E main control-compute.hlsl"`),
at which point `--shader` is redundant but still required. Worth a line in
SKILL.md's step 4, since non-default-profile controls are common.

## 8. A harness-as-compiler bypasses `triage.py`'s path redaction

`triage.py` redacts absolute paths to `<cache>` / `<triage>` / `<repo>` in the
lines **it** writes — the `# exe:` and `[exe]` header lines. It does not touch
the captured program's stdout, and it has no reason to. So a harness that
prints a path (mine printed `dll: <the dxcompiler.dll under test>`) leaks an
absolute path into every capture, and any file the harness writes *itself*
(here `measure.json` and the release-history report) is outside the convention
entirely.

Caught by the orchestrator, not by me. The fix is that **both writers redact**:
`refl3237.cpp` grew a `Redact()` mirroring `triage.py`'s token order, deriving
the roots from its own `GetModuleFileNameW` so the rule holds however it is
invoked; `measure.py` has the Python equivalent. Generalisation for the
harness-as-compiler pattern: *if you write a file or print a path, you own the
redaction* — inheriting it from `triage.py` only covers the wrapper lines.

Worth checking for at the point the harness is registered, since the artifacts
are committed and the leak is invisible in normal use.

## 9. A path-leak scan needs a control, because JSON hides the pattern

Scanning my own directory for `C:\prj\` found eight files and **missed
`measure.json`** — the one file the orchestrator flagged. JSON escapes each
separator, so the bytes on disk are `C:\\prj\\...`, and a regex for `C:\prj\`
does not match `C:\\prj\\`. The scan reported a confident partial clean.

This is the absence-check failure mode the skill already warns about, in a new
disguise: the tool was right, the pattern was wrong, and nothing errored. Two
habits that would have caught it:

- Use a pattern tolerant of escaping — `C:\\\\?\\\\?(prj|Users)` matches both
  the raw and the JSON-escaped form.
- **Run the scan against a known-bad string first.** I now write one line
  containing a real leaked path to a scratch file and confirm the pattern
  fires before trusting a `CLEAN` result. An absence check that has never been
  seen to fire is not evidence.

Same principle as a no-match control on a predicate, applied to the greps used
to verify one's own work rather than to the compiler.
