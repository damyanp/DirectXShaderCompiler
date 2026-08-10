# Method notes — issue 5293, batch batch-013

For a later collation session. Nothing here has been applied to `SKILL.md` or `scripts/`.

---

## 1. `bisect` does not flag `Unknown HLSL version` as an invalid probe

Four releases (v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106) reject `-HV 2021` outright:

```
dxc failed : Unknown HLSL version: 2021        exit 1
```

They never compiled the repro, but `bisect` scored them **`no-repro`**, identical to a
release that compiled it and was fine. On this issue the mistake was harmless — the real
boundary is later — but on an issue whose transition sits near v1.6.2112 it would
manufacture a boundary that is not there, in the same direction as the "invents a bug"
failure the skill already warns about.

Suggested: add `Unknown HLSL version` to the invalid-probe markers, next to whatever already
recognises an unsupported profile. It is a fixed, unambiguous driver string.

## 2. A second class of invalid probe that no output marker can detect

Releases v1.6.2112 through v1.7.2212.1 compile the repro happily and exit 0. They are still
not evidence, because the code under test — the uninitialized out-parameter analysis — did
not exist until `1380cf88e` (v1.7.2308). They are "valid probe, wrong question".

No string in the output can reveal this. The only way to see it is a **behavioural
feature-presence control**: a shader that makes the subsystem announce itself. Here
`control-outparam-presence.hlsl` provokes

```
warning: parameter 'result' is uninitialized when used here [-Wparameter-usage]
```

which is absent up to v1.7.2212.1 and present from v1.7.2308 — matching
`git merge-base --is-ancestor 1380cf88e <tag>` exactly.

Suggested for `SKILL.md`: when a bisect returns "clean at the old end", require a presence
control before reading that as a negative. Feature-gated repros silently convert "the
feature was not there yet" into "the bug was not there yet", which is the difference between
a real fix and an illusory one. This generalises well beyond this issue.

## 3. `bisect` cannot probe an alternative shader

`bisect` takes `--match` but not `--shader`; it always runs the issue's `repro.hlsl`. When a
defect has two manifestations that need **different sources** — here a Debug assert from one
file and a Release memory fault from a larger one — only one of them can be bisected by the
tool. The Release history in `notes.md` had to be produced by a hand-rolled matrix
(`measure-releases.py`).

Suggested: `bisect --shader`, mirroring `run --shader`. Cheap, and it is exactly the shape
the skill's own "compose predicates with `any_of`" advice runs into.

Related note on that advice: here a **second predicate was not needed**. A single
`internal_failure` covered both `0xE0000001` (Debug assert) and `0xC0000005` (Release access
violation) — verified, not assumed, by scoring the release binary with the tool and watching
it return `repro`. What differed between manifestations was the *input*, not the signature.
Worth saying explicitly in `SKILL.md`, because the natural reading of the current text is
that two symptoms imply two predicates.

## 4. Registering a shipped release as a compiler is the way to score a Release symptom

`bisect` reports pass/fail but the per-release captures are not scored variants. Registering
the shipped binary —

```
triage.py compiler --id rel-1.9.2607-5293 --exe .cache\compilers\releases\v1.9.2607\bin\x64\dxc.exe
triage.py run --issue 5293 --compiler rel-1.9.2607-5293 --shader repro-release-crash.hlsl --label release-crash --expect match
```

— produces an ordinary audited capture with the predicate applied, which is what made the
"same binary, one shader exits 0 and another access-violates" comparison citable. Follows the
existing per-issue harness convention already visible in the registry
(`main-debug-refl2952`, `main-debug-fc`).

## 5. `$LASTEXITCODE` is destroyed by piping through `Select-Object -First N`

```powershell
& $dxc ... 2>&1 | Select-Object -First 5      # $LASTEXITCODE is now wrong
& $dxc ... 2>&1 | Out-String                  # $LASTEXITCODE is correct
```

`Select-Object -First` stops the pipeline early, and the exit code observed afterwards is not
the compiler's. This silently turns a crash into a clean run in exactly the measurements that
matter most. Cost me one wrong intermediate reading before I noticed. Worth a line in the
skill's PowerShell section, next to the existing pager warning.

## 6. `cdb` must be launched with an argv list, not a quoted command string

The skill warns about `cdb` invocation in PowerShell. The concrete failure from Python is
different: `cmd /c "<quoted cdb path> ..."` fails on the quoting, while
`subprocess.run([cdb, "-c", ..., exe, ...])` works. Both captures here
(`manual-case-assert-stack.txt`, `manual-case-ndebug-path.txt`) came out of the argv form.

Continuing past the assert with `gh` in cdb is a good general trick for this class: it
emulates what an `NDEBUG` build does without needing a Release build with symbols, and it is
how the out-of-bounds cascade in `manual-case-ndebug-path.txt` was obtained.

## 7. `capture-cdb.py` repo-root depth

`HERE.parents[4]` is wrong for a script living in `data/issues/<n>/`; the repo root is
`HERE.parents[5]`. Any new per-issue script copied from an older one should be checked, since
the symptom is a path that merely looks plausible and `check_paths.py` will not catch a
*wrong* root, only a leaked one.

## 8. `sql` subcommand takes a positional query

`triage.py sql --query "..."` is rejected; it is `triage.py sql "..."`. Minor, but the error
message does not suggest the right form.

Observed schema, in case it is useful: `compilers(id, exe_path, git_commit, version,
built_at)`, `releases(tag, published_at, build_date, asset_name, bisectable, prerelease,
cached_path)`. There is no `seed_local` column despite the skill's wording.

## 9. Draft comment: issue reference form

The batch instructions for this issue forbade writing the `#`-prefixed issue number or an
issue URL anywhere that
could reach a git commit message, because a cross-reference on a watched thread cannot be
deleted. `SKILL.md` (~L1454) asks the draft to open with a callout naming the issue *as a
link*. I resolved this by naming it in plain text ("issue 5293") with no `#` and no URL, and
by opening with both an HTML comment (as the batch instructions required) and the rendered
`> [!WARNING]` callout (as `SKILL.md` requires, and for the reason it gives — HTML comments
are invisible when the file is browsed on github.com).

Flagging it because the two documents genuinely conflict, and the resolution should be a
deliberate policy rather than each worker's judgement. Suggest `SKILL.md` state the safe form
directly.
