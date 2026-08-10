# #4168 — method notes

Observations for the batch-level method review. Nothing here belongs in `comment.md`.

## 1. `cmd.txt` can hold a multi-tool sequence, but only via a harness

The brief asked whether `cmd.txt` can express a link repro. It can, and the whole sequence is
there literally — but only because the registered "compiler" is a harness. `triage.py run`
sends **every** line of `cmd.txt` to the single registered executable, so a three-executable
repro (`dxc`, `dxl`, `dxa`) needs `run-link4168.cmd` → `link4168.py` to dispatch on the leading
token. That is SKILL.md's sanctioned harness-as-compiler pattern and it works, but two things
about it were not obvious and cost time:

- **`--args` is one string, so a chain needs an in-argv separator.** `triage.py run --args`
  replaces the whole command list with a *single* command. Every control and every release
  probe here is a chain, so `link4168.py` accepts a bare `;` token as a separator inside its
  own argv. Without that, controls could not be expressed as tool-made captures at all and
  would have degraded into hand-run `manual-case-*.txt` files, which `reindex` never re-scores.
  Worth considering whether `triage.py` should support this directly for linker issues.
- **`bisect` must not be run and the error message is the only guard.** It substitutes each
  release's `dxc.exe` for the registered compiler; here that would feed harness argv to a bare
  `dxc.exe` and produce an inverted history that still looks plausible. The replacement is an
  issue-local matrix (`measure.py`) that holds the harness fixed and varies the producer via
  `--release <tag>`. This is now the second issue to need one; it may deserve to be a
  `triage.py` subcommand rather than per-issue code that each triager rewrites.
- **A hand-rolled matrix has to remember `--expect` on both arms.** The first run of
  `measure.py` left the repro arm unpinned, on the reasoning that a history probe measures
  rather than asserts. `audit` flagged all 20, and it was right: once the measurement exists,
  recording it as `--expect` is what makes `reindex` re-check the boundary instead of silently
  re-scoring it. The ordering is the whole safeguard — measure, then pin from the captures,
  never pin first. A generic matrix subcommand should do this automatically on a second pass.

## 2. No release ships `dxl.exe` or `dxa.exe` — measured, 0 of 21

`survey-release-tools.py` → `manual-case-release-tools.txt`. Every release archive contains
`dxc.exe` and `dxcompiler.dll` and nothing else executable that matters here. Consequences for
any future linker or reflection issue:

- **`dxl` on a release can only be spelled `dxc.exe -link`.** `tools/clang/tools/dxl/dxl.cpp`
  is a `main` that appends `-link` and calls `dxc::main`, so it should be identity — but
  SKILL.md is right that a deviation must be measured, and `check-dxl-equivalence.py` does:
  byte-identical containers on ground truth, with a third arm that hashes differently so the
  comparison is provably alive. Recommend future linker issues reuse that script rather than
  re-deriving the argument from source.
- **The reflection reader cannot vary with the producer.** There is no release `dxa`, so the
  reader is pinned to the local build. That is only safe with a per-release feature-presence
  control, which is why `measure.py` runs `relctl-<tag>` on all 20 releases. Recommend this be
  stated in SKILL.md as a standing requirement for any producer/reader-split matrix, not just
  as a general principle — it is easy to skip when 20 extra captures feel like clutter.

## 3. `dxa --version` leaks an absolute path into whatever captures it

`dxa.exe` has no `--version`; it responds with an "unknown argument" diagnostic that quotes its
own **absolute path**. A harness that naively forwards `--version` to each dispatched tool
therefore writes a machine path into the compiler registry and into every capture header.
`link4168.py` special-cases this in `emit_version()`. Anything that shells out to `dxa` should
assume its diagnostics are path-bearing.

## 4. Absence predicates: `Size:` survives when the members do not

The symptom is `Num Variables: 0`, an absence, so the predicate needs positive anchors. A
useful concrete finding: in the broken v1.6.2112 dump the cbuffer still reports its correct
`Size: 80` while reporting zero members. So "the dumper reached the buffer and knows how big it
is" is an anchor the symptom genuinely cannot satisfy for free — a better anti-vacuity clause
than anything derived by reasoning about the dump format. Reading the *broken* output before
finalising the predicate is what surfaced it; that ordering is worth making explicit in the
method.

## 5. Prior art that predicts the fix exists is not a measurement

`preserve_cb_types.hlsl` was in the tree before any compiler ran here, and it was tempting to
treat "the regression test exists" as the answer. It is not: the test covers
`vs_6_5`/`vs_6_6`/`vs_6_7` and the reporter's configuration is `ps_6_0`, which the test never
exercises. The release matrix was needed to establish that `ps_6_0` is also fixed. Recording
prior art in `expected.md` as a *prediction to be tested* rather than a conclusion worked well
and is worth keeping as a habit.

Related and unresolved, but visible from the source: `LoadDxilResourceBase` still reads
`HLSLType` only under `IsSM66Plus()` (`lib/DXIL/DxilMetadataHelper.cpp:732`), i.e. the
reporter's Problem 2 was addressed on the emit side, not the load side. End-to-end behaviour is
correct, so this is not a defect claim — but a future issue in this area should not be
surprised by the asymmetry.

## 6. Cross-issue, deliberately kept out of the draft

`bf015d2e1`'s commit message ends with `TODO: investigate` issue **5202**. That is the fix
commit's own follow-up thread and may be relevant to whoever collates this batch. Per the
brief, no cross-issue claim appears in `comment.md`.

## 7. Tooling friction

- **`triage.py run` prints an absolute path, and a script that captures its output leaks it.**
  `run` reports `output: <absolute path>` on stdout. `measure.py` tees `run`'s output into
  `manual-case-release-matrix.txt`, so the first version of that file carried 40 machine paths
  and failed `check_paths.py` — the only leak this issue produced. Fixed at the source rather
  than by hand: `measure.py` now folds the workspace root to `<repo>` before printing, and the
  transcript was regenerated by re-running the matrix, so re-running the script still yields
  exactly what is on disk. No allowlist entry is needed for this issue; the paths were a layout
  detail this triage introduced, not evidence. A driver-side redaction helper in `triage.py` —
  or having `run` print the path the way `display_exe` already prints executables — would
  remove a trap that every matrix script has to rediscover.
- **`check_paths.py` is repository-wide, so in a parallel batch it reports other workers'
  files alongside your own.** While finishing this issue it also listed hits under another
  issue's directory and under the batch report, neither of them this issue's to fix, which
  makes a shared gate read as a local failure and invites a worker to "fix" someone else's
  file. A `--issue`/`--path` filter would let a worker verify its own directory in isolation.
- `grep`/ripgrep through the agent tool silently returns zero matches for anything under
  `.github/` (hidden directory). `Select-String`, `git grep` and `rg --hidden` all work. This
  is a silent wrong answer, not an error, and it is a trap for any triage that greps its own
  skill directory.
- PowerShell has no heredoc, so `python -c` with multi-line source is unreliable; every
  non-trivial script here is a real `.py` file, which also makes them re-runnable evidence.
- `triage.py compiler` warns that the `--commit` short SHA does not appear in the harness's
  version string. Expected for a harness — the version string is the harness's, not `dxc`'s —
  but it means the automatic provenance check is inert for every harness issue, and the
  controlled `git diff` check has to be run by hand instead. Worth a note in SKILL.md next to
  the harness pattern.
