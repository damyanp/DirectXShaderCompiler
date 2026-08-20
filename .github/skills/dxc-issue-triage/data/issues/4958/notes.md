# Notes — #4958: Compiling hull shader with unused globals causes internal compiler error

## Ground truth

`main-debug`, registered at `.cache/compilers/main-debug.json`:

- `dxc --version`: `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage,
  7665270b9)` — checked directly (`build\Debug\bin\dxc.exe --version`) before trusting any
  capture, matches the registered `main-debug.json`.
- Registered public-upstream commit: `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (2026-08-12,
  "[HLSL] Add LinAlg descriptor I/O offset, stride and layout coverage (#8762)"). The binary
  self-reports the fork-local build id `7665270b9`, which is what `--version` will always show
  and does not resolve publicly; per this batch's brief the compiler source has already been
  verified equivalent to the cited upstream commit, so this triage cites
  `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` and not the self-reported id. As a sanity check
  (not a re-derivation of that equivalence work), `git merge-base --is-ancestor
  89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` exits 0 in this checkout, i.e. the cited
  commit is a real, resolvable ancestor of the current tree rather than a dead SHA.

## Repro

The issue body is a single self-contained `.hlsl` file plus the exact command line, both
copied verbatim into `repro.hlsl` / `cmd.txt` (`-T hs_6_6 -E mainHS -Fo output.dxil
repro.hlsl`, source filename swapped from the issue's `debug_hs.hlsl`). Repro quality:
`complete` (see `expected.md`, written before any probe ran).

## Primary result: still reproduces

```
$ dxc -T hs_6_6 -E mainHS -Fo output.dxil repro.hlsl
[exit] 3758096385   (0xE0000001)
Internal compiler error: LLVM Assert
```
(`out-main-debug.txt`). `0xE0000001` is the C++-exception-style assert form (SKILL.md's exit
code table), which `match.json`'s `internal_failure` predicate keys on directly — this is not
a "nonzero exit therefore crash" guess. `match.json`'s note records that this exit status is a
crash without keying on the printed text at all, exactly because that text is not guaranteed
to be stable across configurations (see the Debug/Release split below).

## What the actual crash is (not just "an access violation")

Using the incantation for a C++-exception-style assert (`sxe -c "kb 12; gh" e0000001; g; q`,
via `get_stack.py`, which passes the argv list directly to `subprocess.run` rather than through
another shell — see that file and `manual-case-assert-stack.txt` /
`manual-case-assert-stack-full.txt`):

```
Error: assert(Index < Length && "Invalid index!")
File: <repo>\include\llvm/ADT/ArrayRef.h(197)
Func: llvm::ArrayRef<class llvm::Value *>::operator []
```
called from (innermost first):
```
dxcompiler!llvm::ArrayRef<llvm::Value *>::operator[]
dxcompiler!StoreVectorOrStructArray
dxcompiler!`anonymous namespace'::SROA_Helper::RewriteForStore
dxcompiler!`anonymous namespace'::SROA_Helper::RewriteForScalarRepl
dxcompiler!`anonymous namespace'::SROA_Helper::DoScalarReplacement
dxcompiler!`anonymous namespace'::SROAGlobalAndAllocas
dxcompiler!`anonymous namespace'::SROA_Parameter_HLSL::runOnModule
```
This is an exact match for the one comment on the issue (Keenuts, 2023-01-26): "always in the
ScalarReplAggregatesHLSL.cpp file, around the SROA... Tries to run the transform on the
texture2D array, so before it's removed because unused." The crash is an out-of-bounds
`ArrayRef` index inside `StoreVectorOrStructArray`, reached while SROA rewrites a store into
the (unused, but still SROA-visible) `gProjTextureMaps` resource array. `gh` ("go handled")
then continues execution past the trapped assert exactly as an `NDEBUG` build would, and hits
an access violation (`0xC0000005`) in the same call chain — confirming the Debug assert and a
Release-configuration access violation are the same defect surfacing at different macro
expansions of the same unchecked index, not two different bugs.

## Controls

| control | file | command | expect | result |
| --- | --- | --- | --- | --- |
| remove both unused globals | `control-no-globals.hlsl` | same args | no-match | `no-repro`, exit 0 (`variant-no-globals-main-debug.txt`) — the predicate does not fire on ordinary code |
| SPIR-V target | `repro.hlsl` w/ `-spirv` | `-spirv -T hs_6_6 -E mainHS -Fo output.dxil repro.hlsl` | no-match | `no-repro`, exit 0 (`variant-spirv-main-debug.txt`) — corroborates the one maintainer comment that this is DXIL-lowering-specific |

Both controls behave as predicted, so the predicate discriminates: it does not fire on a
trivially-clean variant of the same shader, and it does not fire under a different backend that
the maintainer already said was unaffected.

## The reporter's ARRAY_SIZE table, re-tested as hypotheses

The issue body claims `ARRAY_SIZE` 0 and 2 "appear to succeed", 1 read-access-violates at
`0xFFFFFFFFFFFFFFFF`, and anything `>2` read-access-violates at `0x0000000000000000`. Re-tested
against `main-debug` as `--hypothesis` runs (not controls — these are predictions about the
bug's shape, not invariants the instrument must satisfy):

| ARRAY_SIZE | predicted | main-debug result | outcome |
| --- | --- | --- | --- |
| 0 | ok | no-repro, exit 0 | supported (`variant-arraysize-0-main-debug.txt`) |
| 1 (as filed) | crash | repro, 0xE0000001 | supported (`out-main-debug.txt`) |
| 2 | ok | **repro, 0xE0000001** | **refuted** (`variant-arraysize-2-main-debug.txt`) |
| 3 | crash | repro, 0xE0000001 | supported (`variant-arraysize-3-main-debug.txt`) |
| 5 | crash | repro, 0xE0000001 | supported (`variant-arraysize-5-main-debug.txt`) |

Only the empty array (`ARRAY_SIZE 0` — i.e. no descriptor slots at all, nothing for SROA to
touch) is clean today; every non-empty size tried (1, 2, 3, 5) crashes on `main-debug`. The
reporter's claim that size 2 was fine does not hold on current `main`/ground truth — it may
have been sensitive to stack/heap layout specific to their build or machine (this is an
uninitialised/out-of-bounds index read, so its exact behaviour is not guaranteed to be stable
across builds), or it may simply have changed since v1.7.2212. Either way, the simpler and more
robust characterisation on current ground truth is "any non-empty `ARRAY_SIZE` crashes",
which is a *stronger* form of the reported bug, not a weaker one.

## History

`bisect --issue 4958` (full output in the session; per-release captures committed as
`out-<tag>.txt`):

- `v1.4.1907`, `v1.5.2010`: `invalid-probe` — both answer `error: invalid profile hs_6_6`
  (`out-v1.4.1907.txt`, and the same reason for v1.5.2010): Shader Model 6.6 did not exist yet,
  so these releases never reached the code under test. Excluded from the range rather than
  counted as clean, per SKILL.md's `invalid-probe` handling.
- `v1.6.2104`: **no-repro**, exit 0, clean compile (`out-v1.6.2104.txt`). This is the oldest
  release that can express `hs_6_6` at all, so it is the effective floor of this issue's
  history (not the general v1.4.1907 floor, which cannot compile this profile).
- `v1.6.2106` onward (`v1.6.2106`, `v1.6.2112`, `v1.7.2212`, `v1.8.2403.1`, `v1.9.2607`) all
  **reproduce**. `bisect` reports `regressed-in v1.6.2106 (last good: v1.6.2104)`.
- `v1.9.2607` is the newest catalogued stable release (`SELECT tag, build_date FROM releases
  ORDER BY build_date DESC` puts it first) and it still reproduces — so this is not a
  regression that was later fixed; it has been broken in every stable release capable of
  compiling `hs_6_6`, for the issue's entire life, and remains broken on `main-debug` today.
- History is monotonic across every point actually measured (one clean release, then crashing
  from v1.6.2106 through the newest stable release and `main-debug`), so `--linear` was not
  needed; nothing in the thread suggests a fix-then-regress shape to check for.
- `v1.7.2212` — the exact release the issue was filed against — reproduces with stderr
  `Internal compiler error: access violation. Attempted to read from address
  0xFFFFFFFFFFFFFFFF` (`out-v1.7.2212.txt`), which matches the reporter's prose ("1 is a read
  access violation at 0xFFFFFFFFFFFFFFFF") verbatim for the address, corroborating that this
  capture is measuring the reporter's actual configuration. `v1.6.2106`, the first bad release,
  shows the identical text and address (`out-v1.6.2106.txt`).
- No PR, branch or commit is named anywhere in the issue body, comment or timeline
  (`gh api .../timeline` returns only `commented`, `labeled`, `milestoned` → "Dormant",
  `added_to_project_v2`, `project_v2_item_status_changed`; zero `cross-referenced` events), so
  there is no "fix landed but unreleased" possibility to check — this is a claim about
  mainline DXC throughout, and it is still true on mainline DXC today.

## Compiler Explorer

Public issue in this public repo, so a link is in scope (SKILL.md "Only public repros go to
Compiler Explorer"). `godbolt --issue 4958 --compilers "dxc_1_6_2112,dxc_trunk"`:

- `dxc_1_6_2112` (CE's oldest DXC, released after this issue's regression point):
  `Program terminated with signal: SIGSEGV`, exit 139 — CRASH. Consistent with the local
  history: CE's earliest available DXC is already inside the broken window this triage found
  (`regressed-in v1.6.2106`, and 1.6.2112 > 1.6.2106).
- `dxc_trunk` (rolling build of current upstream): `error: cast<X>() argument of incompatible
  type!`, exit 5 — CRASH. Per SKILL.md's exit-code table, that message is the
  `llvm::cast<X>()` type-mismatch form of an internal failure (thrown as `hlsl::Exception`,
  reported as E_FAIL/exit 5 truncated on CE's Linux host), not an ordinary diagnosed error —
  the tool correctly classifies both panes as CRASH.
- Full pane text archived in `manual-case-godbolt-verify.txt` (both panes, not just the first
  line). Short link read back and verified against `GET
  /api/shortlinkinfo/<id>` — the stored source (including the `godbolt-note.txt` banner) and
  both panes' compiler ids/arguments match exactly what was sent.
- Link: https://godbolt.org/z/zdcvTzcd7
- Limits that apply here (SKILL.md step 7): CE runs **Release** builds and cannot date
  anything before v1.6.2112, so it corroborates but does not extend the release history found
  locally; it does not overrule the local Debug ground truth. `-Zi -Qembed_debug -Fc -` are
  appended to both panes automatically, which is irrelevant here since neither predicate nor
  finding depends on debug-info mode.

## Assessment

The bug is real, still present in `main-debug` (built at the registered upstream commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`), still present in the newest catalogued stable
release (`v1.9.2607`), and still present in CE's rolling `dxc_trunk` build under a Linux
Release configuration — three independent measurements (local Debug ground truth, a cached
stable release binary, and a differently-built rolling binary on a different OS) that all show
an internal failure on the same input. The root cause is precisely located: an out-of-bounds
`ArrayRef<Value*>` index inside `StoreVectorOrStructArray`, reached from HLSL's SROA pass while
it rewrites a store touching the unused `Texture2D` array global, before that global is
eliminated as dead. This corroborates and sharpens Keenuts' 2023-01-26 comment rather than
contradicting it. The regression window (`v1.6.2104` clean → `v1.6.2106` broken) is real and
has never closed since.

The one place this triage's re-testing diverges from the issue text is the `ARRAY_SIZE`
table: size 2 is no longer (or was never reliably) "ok" — it crashes today just like every
other non-empty size tried. That does not make the issue text stale in the sense SKILL.md
means (nobody's maintainer comment asserts something the compiler now contradicts); it is a
narrower discrepancy about one specific data point in the reporter's own exploratory table, so
no `--text-stale` claim is recorded.

## Suggested action

`still-valid-keep-open`. This is a real, precisely located, still-reproducing crash on
ordinary-looking (if unusual) shader code, unfixed across three years and every measured
release from v1.6.2106 to v1.9.2607 plus current `main-debug` and `dxc_trunk`. Nothing here
supports closing it, and nothing supports downgrading its existing `bug`/`dxil`/`crash`
labels — if anything the found stack trace makes a stronger case for exactly those labels than
the issue body alone did.
