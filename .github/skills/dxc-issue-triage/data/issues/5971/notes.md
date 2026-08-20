# #5971 — "ASAN alloc_dealloc_mismatch false positive on Ubuntu Linux when using libc++ package"

**Status: `not-compiler-verifiable`.** This is a CI/toolchain-environment issue: the reported
defect is an ASAN false positive attributed to Ubuntu's packaged libc++/libc++abi, triggered by
ordinary C++ exception handling inside `dxclib`, not by anything a compiled shader can exercise.
No `repro.hlsl`, `cmd.txt` or `match.json` were written — see "Why there is no predicate" below.
The evidence is the current CI configuration plus the state of the upstream bug trackers the
reporter cited.

Ground truth: `main-debug`, Debug build, self-reporting
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`, `dxc.exe`
version string confirmed identical to the string reproduced by directly invoking
`build\Debug\bin\dxc.exe --version`. Registered compiler `git_commit`:
**`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`**, matching this batch's stated ground truth
exactly. Verified by tree, not just by SHA: `git merge-base --is-ancestor 89e2f98e2... HEAD`
exits 0 (it is a real, public, already-merged upstream commit, not a fork-local one), and
`git diff --name-only 89e2f98e2... HEAD -- . ':!.github/skills/dxc-issue-triage'` returns
**0 files** — the working tree's compiler source is identical to that commit outside the
triage skill directory. Control: the same query against an older commit
(`eff900d54`, used as ground truth in an earlier batch) returns 46 changed files, so the query
can detect differences and the empty result above is not a null query.

## What was measured

This issue cannot be tested by compiling HLSL — there is no shader input that could turn an
ASAN allocator-mismatch false positive (in libc++abi's exception unwinding) on or off. Instead,
the two checkable facts are (1) what DXC's own CI does today, and (2) what state the upstream
bug reports the issue cites are in.

### Finding 1 — the workaround from the issue's own linked PR is still present, unchanged

The issue's second comment (`amaiorano`, 2023-11-03) says the fix is to set
`ASAN_OPTIONS=alloc_dealloc_mismatch=0` on the Linux ASAN bot. `git log -S"alloc_dealloc_mismatch=0" -- azure-pipelines.yml`
finds exactly one commit introducing it: `63cbf4b58` ("Fix enable asan on pipeline (#5976)",
2023-11-07), whose commit message **names this issue** (`#5971`) verbatim and says:

> Perhaps a future Linux image will include a build of libc++ that does not exhibit this false
> positive, at which point this workaround can be reverted.

That is the maintainer's own stated closing condition. At ground truth `89e2f98e2`,
`azure-pipelines.yml:144` still carries
`ASAN_OPTIONS=alloc_dealloc_mismatch=0` unchanged, and it is still applied to `ninja -C build
check-all` (`azure-pipelines.yml:219`). Nobody has revisited or reverted it since 2023-11-07.

### Finding 2 — the CI toolchain has since moved off the originally-implicated package, but the workaround was never re-tested

At the time of PR #5976 (2023-11-07), the ASAN job used the OS-default compiler
(`CC: clang`, `CXX: clang++`, no version pin) — consistent with the launchpad bug the issue
cites, which is filed against Ubuntu's `llvm-toolchain-14` package. At ground truth, the same
job instead:

* runs on `Ubuntu-24.04` (`azure-pipelines.yml:134`);
* explicitly installs LLVM **18** from `apt.llvm.org` via `llvm.sh 18`, and then
  `libc++-18-dev`, rather than any Ubuntu-distribution default package
  (`azure-pipelines.yml:193-196`);
* pins `CC: clang-18`, `CXX: clang++-18` (`azure-pipelines.yml:141-142`).

So the toolchain identity named in both the issue and PR #5976 (an Ubuntu-packaged, unpinned
default clang/libc++) is no longer what CI uses. This move happened by commit `9009fb8ec`
("Fix Test Breakage on WSL (#8263)"), dated 2026-03-12; that commit's diff shows
`azure-pipelines.yml` as a whole-file addition rather than an incremental edit (consistent with
a prior history rewrite noted elsewhere in this skill's method notes), so the exact date the
clang-18/libc++-18-dev switch itself landed could not be pinned more precisely than "on or
before 2026-03-12" from this repository's visible history. Either way, **the
`alloc_dealloc_mismatch=0` workaround was carried forward unchanged across that toolchain
change** — nobody removed it to test whether the newer, differently-sourced libc++ package
still exhibits the mismatch.

### Finding 3 — both upstream bugs the reporter cited are now closed

The issue body cites two upstream LLVM reports as the known root cause:

* `llvm/llvm-project#59432`, "[libc++] AddressSanitizer: alloc-dealloc-mismatch in
  std::logic_error" — **state: closed**, `closed_at: 2024-12-21T23:11:36Z` (fetched via
  `gh api`/`GET https://api.github.com/repos/llvm/llvm-project/issues/59432`, read-only, public
  repo).
* `llvm/llvm-project#52771`, "AddressSanitizer error when using libc++ from apt.llvm.org" —
  **state: closed**, `closed_at: 2025-02-02T20:28:53Z`. This second report is specifically
  about **apt.llvm.org** packages, which is exactly where DXC's CI now sources `clang-18` and
  `libc++-18-dev` from (Finding 2), so it is the more directly relevant of the two.

Both closures predate the ground-truth date (2026-08-19) by well over a year, and #52771's
closure also predates DXC's move to `apt.llvm.org`-sourced LLVM 18 as far as this repository's
visible history can establish. This is consistent with — but does not prove — the second half
of the maintainer's own closing condition ("a future Linux image will include a build of libc++
that does not exhibit this false positive") now being true for DXC's current CI toolchain. It
is **suggestive, not conclusive**: "closed" on an upstream tracker does not by itself confirm
which package version absorbed the fix, or that `apt.llvm.org`'s libc++-18 build in particular
incorporated it by the time DXC's CI adopted it. Confirming that would require actually running
the ASAN job (or an equivalent local ASAN+libc++-18 Linux build) with the workaround removed —
out of scope for this Windows-only, no-rebuild triage session.

### Finding 4 — the originally-failing test is still exercised the same way

`tools/clang/test/DXC/recompile.test` (named in the issue's stack trace) still exists at ground
truth and still invokes `%dxc -dumpbin ...` on the recompiled blob, which is the call path that
reaches `DxcIncludeHandlerForInjectedSources::LoadSource`
(`tools/clang/tools/dxclib/dxc.cpp:709` in the pasted trace) — so the code path the ASAN report
was raised against is still in active use by `check-all`, not something since removed.

## Why there is no predicate

`match.json` and `cmd.txt` were deliberately not written. Every possible `dxc` compile result —
success, failure, any diagnostic, any DXIL — is compatible with this report being entirely
true, because the alleged defect is in the platform C++ runtime's ASAN interceptors, not in
anything shader-input-dependent. A predicate built over compiled output could not discriminate
this issue's `repros` from `does-not-repro`; per the skill, a predicate that cannot fail is
worse than none. `triage.py audit` does not require either file, and there is no `.hlsl` in
this directory, so nothing is left unchecked by their absence.

## Limitations

* **No ASAN-instrumented Linux build was run.** This triage machine is Windows, and building
  one would require a shared, non-trivial rebuild (`LLVM_USE_SANITIZER=Address`,
  `LLVM_ENABLE_LIBCXX=On`, `libc++-18-dev` on Linux) explicitly out of scope for this session
  ("no shared edits/reindex/rebuild/source changes"). All conclusions here rest on reading CI
  configuration and public upstream-issue metadata, not on reproducing or refuting the ASAN
  report directly.
* **Upstream-issue closure is not a changelog.** Neither #59432 nor #52771 was read in full
  (only body/state/dates for #59432, and body/one early comment plus state/dates for #52771);
  their closing rationale (a real libc++ fix vs. e.g. staleness) was not independently
  confirmed here.
* **The `azure-pipelines.yml` history gap.** Because commit `9009fb8ec` shows the whole file as
  newly added rather than incrementally diffed, the exact date the CI moved from the
  originally-implicated OS-default clang to `apt.llvm.org` clang-18/libc++-18-dev could not be
  pinned from this repository's visible commit history; only "before 2026-03-12" is established.
* **Cross-reference timeline.** `gh api .../issues/5971/timeline` shows two cross-references,
  both from unrelated external repos (`r-hub/rhub#598`, `libhal/libhal-mock#11`, both citing
  this issue only as an example of the general ASAN packaging problem); neither is a DXC PR and
  neither indicates this issue was independently resolved in this repository.

## Verdict

* status **`not-compiler-verifiable`** — the compiler is not the instrument; this is a CI
  toolchain/packaging issue
* repro quality **`prose-only`** — a pasted ASAN log plus links to upstream trackers, no shader
* history **`n/a`** — not bisectable; there is no release-over-release compiler behavior to scan
* confidence **`high`** on what is directly measured (workaround still present unchanged;
  toolchain has moved off the originally-cited package; both cited upstream bugs are closed);
  **not** high on whether the workaround could safely be removed today — that requires actually
  running the ASAN job, which was not done here
* suggested action **`needs-human-judgement`** — reverting the workaround to test whether it is
  still needed (as the maintainer's own PR #5976 message proposed) is a low-risk experiment a
  maintainer with CI access could run directly; this session cannot run or gate CI

`text_stale` was considered and **not** set: the issue's title and body still accurately
describe what was observed and diagnosed in 2023, and the thread's own comments already record
the workaround and the two paths to a "real" fix. Nothing in the issue text contradicts current
behavior; what has changed (the toolchain move, the upstream closures) is context the reporter
could not have had, not a staleness in what they wrote.

## Label proposal

Current: `bug`.

* add **`ci`** — "Continuous integration"; the entire finding and fix live in
  `azure-pipelines.yml`, not in compiler source
* add **`sanitizer`** — "fault detected by sanitizer run"; this is exactly that, and the
  taxonomy has a dedicated label for it that is not currently applied
* add **`linux`** — "Linux-specific work"; the symptom is specific to the Linux/libc++ ASAN bot
* `bug` retained — it did cause real (if false-positive) CI failures and a merged workaround
  PR; not proposing removal, since whether a false-positive ASAN report on a specific packaging
  combination counts as a DXC "bug" is a judgment call I'd rather leave to a maintainer than
  overrule.
