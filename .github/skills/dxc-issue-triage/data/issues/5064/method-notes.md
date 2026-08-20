# Method notes: #5064

Observations from triaging this single issue. Not applied to `SKILL.md` or `scripts/` — per
the per-issue worker boundary, only recorded here for collation to consider.

## `lit --show-tests` needs `build_mode=Release`, not `Debug`, in this environment

`python utils\lit\lit.py --show-tests --param=build_mode=Debug build\tools\clang\test\...` fails
with a `FileNotFoundError` for `llvm-config.exe`, because `lit.cfg`'s `get_llvm_config_props()`
shells out to it for feature detection and only `build\Release\bin\llvm-config.exe` exists on
this machine (the registered ground-truth compiler used for other issues in this batch is the
*Debug* build, `build\Debug\bin\dxc.exe`). Using `--param=build_mode=Release` instead works and
is legitimate here because `--show-tests` only enumerates discoverable tests — it does not
execute `dxc`/`dxv`/FileCheck against any compiler binary — so which build configuration's
`llvm-config` answers the feature-detection questions does not affect the discovery-count result
being measured (config.suffixes/lit.local.cfg content is identical between build configs; only
the tool-existence side of feature detection differs). Worth flagging for collation because any
future issue that needs read-only lit discovery on this machine will hit the same gotcha.

## `lit --show-tests <build-tree-subdir>` can under-report even for genuinely-discovered directories, unless pointed at the build tree's `test` root

Passing a specific build-tree subdirectory straight to `--show-tests`
(e.g. `build\tools\clang\test\CodeGenHLSL`) is not reliable as a "does the *tool* even find
anything here" smoke test on its own — a directory can report "contained no tests" for either of
two different reasons: (a) it is genuinely excluded from discovery (as with `HLSLFileCheck` and
`DXILValidation` here, confirmed by their `config.suffixes = []`), or (b) lit resolves file
discovery against the mirrored *source*-tree path via `test_source_root`/`test_exec_root`, and a
build-tree subdirectory that was never populated by a file-copy step can appear empty even for a
tree that lit's config genuinely includes. In this investigation, pointing `--show-tests`
directly at the three build-tree leaf paths of interest (`HLSLFileCheck`, `DXILValidation`,
`DXC`) gave results fully consistent with each directory's own `lit.local.cfg` (empty for the
first two, ~90 real tests for `DXC`), so reason (a) is confirmed as the actual cause here and not
an artifact of (b) — but this was only established by cross-checking the config file contents
directly, not by trusting the `--show-tests` output alone. Recommend collation record this as a
"verify both ways" rule for any future infra/build-issue triage that leans on `--show-tests`
counts as evidence: pair a "contained no tests" (or a nonzero count) result with an explicit read
of the relevant `lit.local.cfg`/`lit.cfg` before treating it as evidence of the tree's true
discoverability, rather than pointing `--show-tests` at only the top-level
`build\tools\clang\test` and grepping, or only reading `--show-tests` output on its own.

## The exact ground-truth SHA is a shallow ref; use a tag as the negative-control ancestor

`89e2f98e29c289ae8ad9e00dd310104fea9fd7df~200` fails ("unknown revision") because this checkout
fetched that exact SHA shallowly (`git rev-list --count` = 1 for it directly), even though the
currently checked-out branch has full history. The provenance negative control (diff against a
clearly-older point that must show real differences, to prove the positive "0 files differ"
result isn't vacuous) still works fine using a reachable tag instead of a relative ancestor
expression — `v1.4.1907` was used here and reproduced the same 6992-file negative-control result
seen in other issues in this batch (e.g. `4766`). Worth recording since any issue that tries the
`<ground-truth-sha>~N` pattern verbatim (as `4766`'s script did, coincidentally against a
different, non-shallow ref) will hit this exact failure against *this* batch's ground-truth SHA
specifically.

## Zero cross-references means the "still open" determination rests entirely on direct tree inspection

For a `tech-debt`/infrastructure issue with no linked PR anywhere (confirmed via the full
`timeline` API, not just a keyword search), there is no maintainer commit message or PR
description to lean on for "this addressed it." All three findings in `notes.md` (the lit
exclusion, the partial migration with no validator subtree, and the external-validator-coverage
resolution) had to be established by direct measurement (running `lit --show-tests`, reading
`lit.local.cfg` contents, `git log --follow` on the relevant files) rather than by reading a
"Fixes #5064"-style commit trailer. This generalises the same observation made in `4766`'s
method-notes for a different issue: for infra/tech-debt issues, the cross-reference timeline read
during step 1 is often absent entirely, and the deep-dive source investigation isn't optional
supporting evidence — it is the *only* evidence available.
