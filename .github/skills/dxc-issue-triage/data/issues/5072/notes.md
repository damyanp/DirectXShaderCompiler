# #5072 — Header output option `-Fh` results in invalid default identifier for library targets

**Verdict: repros.** Compiling any HLSL library target (`-T lib_6_3`, or any
other `lib_6_*`/`lib_6_x` profile) with `-Fh <file>` and no explicit `-Vn`
produces a header whose byte-array variable is declared under the literal
identifier `g_lib.no::entry` — not a legal C or C++ identifier, because of the
`.` and `::`. Reproduces on ground truth (`main-debug`, commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`, `dxc --version` reports
`1.9.0.5465 (triage, 7665270b9)`) and on all 21 cached releases,
v1.4.1907 (2019-07-15) through v1.9.2607 (2026-07-29).

## Ground truth

`main-debug` is registered at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`. Before
running anything, I verified this the way SKILL.md requires — by tree, not by
SHA: `git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(`7665270b9` is what the binary self-reports in `--version`) shows **zero**
files differing outside `.github/skills/`, so the registered binary's source
tree is provably identical to the cited public commit. `dxc.exe --version` was
run directly and matches the registry (`.cache/compilers/main-debug.json`)
exactly.

## What was measured, and why a harness was needed

`-Fh` writes its header **only to the named file**; nothing about the chosen
identifier ever reaches stdout/stderr (confirmed by reading
`DxcContext::WriteHeader` in `tools/clang/tools/dxclib/dxc.cpp`). A plain
`cmd.txt` + `match.json` run over `dxc.exe`'s own output would score a clean
"no output" on every case regardless of what happened — the same trap
SKILL.md documents for `-P`/`-Fc`.

`fh-header-check.py`/`fh-header-check.cmd` (this directory) is the harness
that brings the artifact into scored output: it runs the real `dxc.exe`
(located via `DXC_FH_REAL_EXE`, defaulting to this repo's own Debug build)
with the exact requested arguments, then reads back whatever file `-Fh`
named and reports whether the declared variable name is a legal C/C++
identifier. It has an explicit `no-declaration` self-test-failure path (a
message that neither matches nor negates the predicate) so a broken regex
cannot silently manufacture a clean result — the mirror image of the
absence-predicate trap SKILL.md warns about. Registered as `main-debug-fh`
with the same commit as `main-debug`, since it wraps that exact binary.

`match.json` is a `contains` predicate on `FH-HARNESS: IDENTIFIER-INVALID`,
which the harness only prints when it found an actual declaration and that
declaration's name failed a strict `^[A-Za-z_][A-Za-z0-9_]*$` check — i.e. it
requires proof the header was produced and parsed, not merely an absence.

`out-main-debug-fh.txt` (primary probe, `-T lib_6_3 -Fh out-header.h
repro.hlsl`): scored `repro`, `FH-HARNESS: IDENTIFIER-INVALID
name='g_lib.no::entry'`, exit 0.

## Controls

Both ran through `triage.py run --args ... --expect no-match` against
`main-debug-fh` and both matched their declared expectation:

| variant | args | result |
| --- | --- | --- |
| `-Vn` workaround (`variant-vn-control-*.txt`) | `-T lib_6_3 -Fh out-header-vn.h -Vn g_MyLibShader repro.hlsl` | `no-repro`, `IDENTIFIER-VALID name='g_MyLibShader'` |
| non-library profile (`variant-non-library-control-*.txt`) | `-T cs_6_0 -E CSMain -Fh out-header-cs.h repro.hlsl` | `no-repro`, `IDENTIFIER-VALID name='g_CSMain'` |

The second control is the one that earns the first: it proves the harness's
predicate can say "no" on the very same source file, and that the defect is
specific to *library* profiles rather than `-Fh` being broken in general —
which also matches the source (below): the sentinel entry name is only
assigned `if (IsLibraryProfile())`.

## Direct compile confirmation (`manual-case-cl-compile.txt`)

The issue's literal claim is a **compile failure** in a real C/C++
translation unit. `gen-cl-compile-check.py` (committed in this directory,
generator for the `manual-case-*.txt` per SKILL.md's rule that every such
file be produced by a small script that echoes the command it runs) feeds
both `out-header.h` (the repro) and `out-header-vn.h` (the control) to the
real MSVC `cl.exe` as both C (`/TC`) and C++ (`/TP`):

- `out-header.h` (no `-Vn`): **fails to compile** as C (`C2143`/`C2059` on the
  `.`) and as C++ (`C2653: 'no': is not a class or namespace name` plus five
  more cascading errors from `::` being parsed as scope resolution).
- `out-header-vn.h` (`-Vn g_MyLibShader`): **compiles cleanly**, exit 0, as
  both C and C++.

This is an independent confirmation that does not share any code with
`fh-header-check.py`'s regex reader — a real compiler, not a pattern match,
rejects the header.

## Source (corroboration, not a substitute for the runs above)

- `lib/DxcSupport/HLSLOptions.cpp:569`: `opts.EntryPoint = "lib.no::entry";`
  — assigned unconditionally whenever `IsLibraryProfile()`, an intentional
  "impossible name" sentinel.
- `tools/clang/tools/dxclib/dxc.cpp:430-432`: `-Fh`'s default variable name,
  absent `-Vn`, is `llvm::Twine("g_", m_Opts.EntryPoint)` — no library-profile
  case.
- `git log --all -S'lib.no::entry'` (repository-wide, not path-scoped — see
  SKILL.md's warning about path-scoped searches missing the true
  introduction): the only source hit is `8e21407ca` ("Add library profile.",
  2017-05-12, Xiang Li). Never touched since.

## History

`release-matrix.py` (committed in this directory) measures history directly,
because **`triage.py bisect` refuses this issue**: its ground truth is the
`main-debug-fh` harness, not `dxc` (`refuse_harness_bisect` in `triage.py`).
Unlike #3237's reflection bug — where a fixed harness `.exe` could have a
release's `dxcompiler.dll` swapped underneath it — `-Fh`'s header-writing code
(`DxcContext::WriteHeader`) lives in the **`dxc.exe` driver itself**, so each
row below runs that release's own, whole `dxc.exe`, via
`fh-header-check.py`'s `DXC_FH_REAL_EXE` indirection. No `triage.py compiler`
registration is needed per release; the script imports
`find_fh_path`/`check_header` directly.

`manual-case-release-history.txt` / `release-matrix.json`: **every one of the
21 cached releases plus `main-debug`** reproduces the library case
(`g_lib.no::entry`) and is clean on the non-library control (`g_CSMain`) — no
`invalid-probe` rows, no exceptions. Combined with the source dating the
sentinel to 2017-05-12 (well before the bisection floor, v1.4.1907,
2019-07-15) and finding no later edit, the history is **always-repro'd**;
there is no regression to bisect. This mirrors, in outcome, `bisect`'s own
short-circuit for a case with no suspected non-monotonicity, but is arrived
at empirically across every cached release rather than assumed from the
endpoints alone.

**Coverage boundary.** 21 is every release tag this cache holds, not every
tag microsoft/DirectXShaderCompiler has ever published — I did not fetch any
additional release to fill a gap, since the source evidence (unconditional
sentinel, unmodified since 2017) gives no reason to expect a hole in the
covered span to matter. The comment says "all 21 releases I could measure"
for this reason.

## Compiler Explorer

**Skipped** (`godbolt --skip`, recorded in `verdict.json`). The defect is
entirely inside `-Fh`'s file output; CE's `/api/compiler/.../compile`
endpoint returns only `stdout`/`stderr`/`asm` text, with no channel for an
arbitrary file a flag asked the compiler to write. I confirmed empirically
that the sentinel name leaves no trace anywhere else: default disassembly of
`repro.hlsl` at `-T lib_6_3`, with no `-Fh` at all, contains no occurrence of
`lib.no::entry` or any variant of it in its text. A CE pane would therefore
show only an ordinary successful library compile, indistinguishable from any
`-Fh`-free case — false reassurance, not evidence.

## Labels

Current: `bug`, `low-hanging-fruit` — both remain accurate; the maintainer's
own comment describes exactly this shape ("we're not going to proactively fix
this... if someone feels inspired to put a PR together... we'd consider it").
Proposing **`shader-linking`** added (its description, "Bugs related to
library targets and linking", matches this issue precisely — the defect is
library-profile-specific by construction) with no removals.

## What I did not measure

- Non-Windows/non-MSVC compilers against the generated header (e.g. clang,
  gcc). MSVC's rejection under both `/TC` and `/TP` is already the strongest
  practical confirmation available in this environment, and the identifier is
  invalid by the C/C++ grammar itself (`.` and `::` cannot appear in an
  identifier token under any compiler), so a second toolchain would not
  change the verdict.
- Other library-profile variants (`lib_6_4` through `lib_6_9`/`lib_6_x`) —
  the sentinel assignment in `HLSLOptions.cpp` is unconditional on
  `IsLibraryProfile()` regardless of shader-model minor version, so this is
  not expected to vary, but was not independently probed profile-by-profile.

## Suggested action

`still-valid-keep-open`. The maintainer's 2024-08-27 comment already settles
the product question (workaround exists, no proactive fix planned, PR
welcome) and #8074's 2026-01-20 duplicate-closure with the identical repeated
stance shows that position was unchanged roughly ten months ago — this triage
adds confirmation that the underlying defect is unchanged on current `main`
and has been present, unmodified, across the compiler's entire probeable
release history; it does not argue for a priority change.

Confidence **high** on the symptom, its cause and its history; nothing here
is in question.
