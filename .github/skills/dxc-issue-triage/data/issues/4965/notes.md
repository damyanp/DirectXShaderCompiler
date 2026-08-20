# Notes — #4965

## What was tested

Ground truth: `main-debug`, registered at `<repo>/build/Debug/bin/dxc.exe`, upstream commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (`dxc --version` reads
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`; the binary
self-reports the fork-local commit `7665270b9`, but `git diff --name-only HEAD
89e2f98e29c289ae8ad9e00dd310104fea9fd7df -- . ':!.github/skills/dxc-issue-triage'` is empty —
no tracked file outside the triage skill directory differs from the cited public commit. As a
control, the same diff against `HEAD~50` lists 97 changed files outside the skill directory, so
the empty result above is a real equivalence, not a diff that can't see anything.)

`repro.hlsl` and `cmd.txt` reproduce the filed source and command verbatim (`-T ps_6_2 -E f`,
the dash-spelling of the reporter's `/T ps_6_2 /E f` — confirmed byte-identical output and exit
code via a `cmd-as-filed` variant using the reporter's own slash spelling, so the spelling
change is cosmetic only).

`match.json` is `internal_failure`, per the skill's "use this for all crash/assert issues"
rule, because the issue reports **three different signatures of one defect** across build
configuration: a Windows access violation (silent, or `Internal compiler error: access
violation. Attempted to ... address 0x...`), a text-only `error: llvm::cast<X>() argument of
incompatible type!` (E_FAIL, caught by the internal_failure text backstop for bad `llvm::cast`),
and a Debug-build assert trap in `ScalarReplAggregatesHLSL.cpp` (`otherwise we flattened a
library function.`) that a maintainer hit at head in Jan 2023. A single message match would
have missed at least two of the three. `control-good.hlsl` (`float4 f() : SV_Target { return
0; }`, same `-T ps_6_2 -E f`) is the negative control and scores `no-repro` as required
(`variant-control-good-main-debug.txt`).

## Result on ground truth

`main-debug` does **not** reproduce a crash. It exits `0x80004005` (E_FAIL, an ordinary
diagnosed error, not an internal-failure status) with:

```
repro.hlsl:1:1: error: recursive functions are not allowed: function 'f' calls recursive function 'f'
int f( int)
^
repro.hlsl:1:1: note: recursive function located here:
```

(`out-main-debug.txt`, `--repeat 10`, 0/10 hits — deterministic, not a case where a
nondeterministic crash happened to not fire.) `-E f` makes `f` the entry point; the source also
calls `f` at global scope to initialize `static int b`, and DXC synthesizes calls to global
initializers inside the entry-point wrapper it builds for `f`. The result is that `f`'s own
wrapper calls `f` — a genuine (if unusual) self-recursion introduced by entry-point lowering,
and the front end's existing recursion check (`err_hlsl_no_recursion`,
`tools/clang/lib/Sema/SemaHLSLDiagnoseTU.cpp`) now catches it before codegen/SROA ever runs,
which is exactly why the Debug SROA assert Keenuts hit in Jan 2023 no longer fires: the
compile never reaches that pass.

## History

`bisect --repeat 5` (binary search; endpoints alone would not have been enough — see below):

| release | verdict | detail |
| --- | --- | --- |
| v1.4.1907 | repro | silent access violation, exit `0xC0000005`, empty stderr (`out-v1.4.1907.txt`) — matches the "internal failure may print nothing" pattern documented in the skill |
| v1.8.2403 | repro | `Internal compiler error: access violation. Attempted to write from address 0x...` (`out-v1.8.2403.txt`) — matches the issue's first quoted message class |
| v1.8.2502 | repro | `error: llvm::cast<X>() argument of incompatible type!`, exit `0x80004005` (`out-v1.8.2502.txt`) — matches the issue's second quoted message exactly |
| v1.8.2505 | **no-repro** | same `recursive functions are not allowed` diagnostic as `main-debug` (`out-v1.8.2505.txt`), 0/5 hits |
| v1.8.2505.1 | no-repro | same diagnostic, 0/5 hits |
| v1.9.2607 | no-repro | same diagnostic, 0/5 hits (`out-v1.9.2607.txt`) |

Result: **fixed-in v1.8.2505** (last reproducing stable release: v1.8.2502). One prerelease,
`v1.2.0-alpha`, had no usable `dxc` asset and was skipped; five prereleases
(`v1.5.2003, v1.8.2306-preview, v1.8.2405-mesh-nodes-preview, v1.10.2605.2, v1.10.2605.24`)
were excluded from the search by policy, none of them inside the transition interval. No
release in the scan was demoted as `invalid-probe` — every probed release, old and new,
actually compiled the repro one way or another, so the fix boundary is not an artifact of a
release rejecting the input before reaching the code under test.

The commit window between `v1.8.2502` and `v1.8.2505` is **162 commits** (`git log
v1.8.2502..v1.8.2505 --oneline`, whole-repo count). None of their titles name recursion,
global-initializer handling, or entry-point wrapping, and the pre-existing recursion
diagnostic's own file history (`SemaHLSLDiagnoseTU.cpp`, `recursive2.hlsl`, `recursive3.hlsl`)
predates this window by years — this fix looks like a side effect of unrelated front-end or
call-graph work in that window rather than a change targeted at this issue. No commit was
built and tested individually (per the task's read-only/no-shared-rebuild boundary for this
single-issue session), so the fix is attributed to the **release window**, not to one commit;
call the attribution strong, not certain.

## Compiler Explorer

Public issue, public repro — CE is in scope. `https://godbolt.org/z/ee6xoP8jz`
(read back and confirmed via `GET /api/shortlinkinfo/ee6xoP8jz`, source and both compiler
argument sets match what was sent):

- `dxc_1_6_2112` (CE's oldest DXC, Linux Release): `Program terminated with signal: SIGSEGV`,
  exit 139 — the Linux face of the same defect, and corroborates Keenuts' 2023-02-01 comment
  that on Linux (asserts disabled) this reaches an invalid pointer load in `GlobalIsNeeded` and
  segfaults rather than hitting SEH.
- `dxc_trunk`: the same `recursive functions are not allowed` diagnostic as `main-debug`,
  confirming the fix is present in a rolling trunk build too (not cited as a second history
  point — `dxc_trunk` is not reproducible over time).

Both panes are archived in `manual-case-godbolt-verify.txt`. `godbolt-note.txt` describes the
SIGSEGV/diagnostic contrast rather than naming a token the note itself would manufacture.

## Assessment against `expected.md`

`expected.md`'s prediction was that this reproduces as an `internal_failure` in one of (at
least) three shapes. That held all the way back to the oldest probeable release and through
v1.8.2502, and stopped holding at v1.8.2505: the compiler now diagnoses the self-recursion
introduced by using a global-initializer-calling function as the entry point, before the
pass that used to crash ever runs. This is a `does-not-repro` / `fixed` verdict, not a
`changed-behavior` one — the new diagnostic is not a different bug, it is the front end
correctly rejecting the same invalid input the whole thread agreed was invalid
("It is invalid shader code that we don't produce a good error for.", llvm-beanz,
2023-01-31). That "don't produce a good error for" is exactly what stopped being true at
v1.8.2505.

No cross-reference events exist on this issue's timeline as of fetch (checked with
`gh api repos/microsoft/DirectXShaderCompiler/issues/4965/timeline`), and this triage session
created none (read-only: `fetch`, `run`, `bisect`, `godbolt`, `labels` only).

## What could not be determined

- The exact fixing commit inside the 162-commit `v1.8.2502..v1.8.2505` window was not
  identified; per-commit bisection would require building a candidate and its parent in an
  isolated worktree, which this session did not do (see boundary note above).
- Whether the fix was intentional (a targeted recursion-detection improvement) or an
  incidental consequence of unrelated call-graph/front-end work in that window is unknown from
  commit titles alone; nothing in the 162 titles names recursion, global initializers, or
  entry-point wrapping.
- The Linux SIGSEGV path (`GlobalIsNeeded`, per Keenuts' comment) was corroborated only on
  CE's `dxc_1_6_2112`, an old release; it was not independently probed against a Linux build of
  the fixed range, since no Linux release asset is in the catalog.
