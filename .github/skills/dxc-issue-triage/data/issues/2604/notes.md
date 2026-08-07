# #2604 — Handle `-Fc` in Compile API

**Verdict: repros.** `IDxcCompiler::Compile` and `IDxcCompiler3::Compile`
reject `-Fc` outright — the result status is `E_INVALIDARG` (`0x80070057`)
with `Unknown argument: '-Fc'` — and when the rejection is suppressed with
`-Qunused-arguments` the compile succeeds and `-Fc` is silently ignored: no
`DXC_OUT_DISASSEMBLY` on the result, no file at the named path. Measured on
`main` (`13730886e`) and on all **21** released `dxcompiler.dll` builds in the
cache, v1.4.1907 (2019-07-15, which predates the issue) through v1.9.2607
(2026-07-29). Nothing has changed in either direction.

The same `dxcompiler.dll`, driven through `dxc.exe`, writes the listing
happily. That split is the whole subject of the issue and follows from the
option-table flags and the API/driver parsing masks.

## The two claims, kept apart

`expected.md` was written before anything ran and separated two claims that
the issue thread conflates. Both were given their own predicate:

| | claim | source | predicate | result |
| --- | --- | --- | --- | --- |
| **A** | the compile API *rejects* `-Fc` with `E_INVALIDARG` | 2020 comment | `match-einvalidarg.json` | **repro** |
| **B** | the compile API does not *honour* `-Fc` — no way to get a listing out of one `Compile` call | issue body | `match.json` | **repro** |
| **C** | `docs/SPIR-V.rst` says these options "are also recognized by the library API calls" | 2020 comment's citation | `match-spirv-doc.json` | **repro** (the doc is wrong) |

`expected.md` predicted `changed-behavior` as the most likely outcome — that
six years would have quietly turned the `E_INVALIDARG` into "accepted and
ignored". That prediction was **wrong**, and the release matrix is what says
so rather than an argument. Recorded here because the pre-registration only
earns its keep if the misses are reported too.

## Why a harness

`dxc.exe` is the one caller that already handles `-Fc`, so no `cmd.txt` +
`match.json` pair over `dxc.exe` output can reach the code under test — it
would measure the opposite of the question. `fc2604.cpp` in this directory is
a small C++ program that calls the API directly:

    IDxcCompiler::Compile   (the interface that existed in 2019)
    IDxcCompiler3::Compile  (added in DXC 1.6)
    IDxcCompiler::Disassemble  (the anchor)

It loads whatever `DXC_FC_DLL` names, so pointing it at a release's
`dxcompiler.dll` measures **that release's** option handling. It is registered
as the compiler `main-debug-fc` via `run-fc2604.cmd`, so `triage.py run`,
`--args` controls, `--expect` and re-scoring all work normally. This is the
harness-as-compiler pattern from #2922/#2923/#3237.

Ten cases per run; each prints a detail block and one `RESULT case=…` line.
Ground truth (`out-main-debug-fc.txt`):

    RESULT case=c1-fc           call=0x00000000 status=0x80070057 object=absent  disasm=absent  fcfile=absent
    RESULT case=c1-fc-qunused   call=0x00000000 status=0x00000000 object=present disasm=absent  fcfile=absent
    RESULT case=c1-baseline     call=0x00000000 status=0x00000000 object=present disasm=absent  fcfile=n/a
    RESULT case=c1-disassemble  call=0x00000000 status=n/a        object=n/a     disasm=present fcfile=n/a
    RESULT case=c3-fc           call=0x00000000 status=0x80070057 object=absent  disasm=absent  fcfile=absent
    RESULT case=c3-fc-qunused   call=0x00000000 status=0x00000000 object=present disasm=absent  fcfile=absent
    RESULT case=c3-baseline     call=0x00000000 status=0x00000000 object=present disasm=absent  fcfile=n/a
    RESULT case=c1-spirv-baseline    call=0x00000000 status=0x00000000 object=present disasm=absent fcfile=n/a
    RESULT case=c1-spirv-fc          call=0x00000000 status=0x80070057 object=absent  disasm=absent fcfile=absent
    RESULT case=c1-spirv-fc-qunused  call=0x00000000 status=0x00000000 object=present disasm=absent fcfile=absent

    SELFCHECK: cases-run=10/10
    SELFCHECK: fc-operand-seen=yes
    SELFCHECK: spirv-codegen=available
    SELFCHECK: baseline-disassembly-bytes=4104

Note `call=0x00000000 status=0x80070057`: the **call** succeeds and only the
result object carries the failure. A caller that checks the `HRESULT` of
`Compile()` and not `GetStatus()` sees success and an empty object. The
harness therefore reports the two separately, and the source evidence
(probes 8 and 9) shows exactly where that split is created.

**Nothing binary is committed.** `.gitignore` in this directory excludes
`bin/`, `bin-build.log` and the scratch `repro-fc.asm`. What is committed is
`fc2604.cpp`, `build-fc2604.cmd` and `run-fc2604.cmd`, which rebuilds
`bin/fc2604.exe` on demand if it is missing. To rebuild by hand:

    cd data/issues/2604 && ./build-fc2604.cmd

No absolute paths appear in any committed artifact. Both writers redact:
`fc2604.cpp` has a `Redact()` for the lines it prints, `measure-2604.py` has
the Python equivalent, and both derive their roots from their own location.
`triage.py` redacts only the lines *it* writes, so a harness's stdout passes
through untouched unless the harness does it itself.

## Why it behaves this way — corroborated from source

Every command below is re-run and captured in
**`manual-case-source-evidence.txt`**; the two absence claims each carry a
known-positive control in that file.

1. **`-Fc` is a driver-only option.** `include/dxc/Support/HLSLOptions.td:505`

       def Fc : JoinedOrSeparate<["-", "/"], "Fc">, …, Flags<[DriverOption]>, …

   No `CoreOption`.

2. **It has never been anything else.** `git log -L 505,505:…HLSLOptions.td`
   returns exactly one commit: `6ee4074a4` (2016-12-28, "first commit").

3. **Two masks, two callers.** `HLSLOptions.h:75` —
   `CompilerFlags = HlslFlags::CoreOption`, used by the library at
   `dxcompiler/dxcutil.cpp:114`. `HLSLOptions.h:77` —
   `DxcFlags = CoreOption | DriverOption`, used by the driver at
   `dxclib/dxc.cpp:1437`. Options lacking the requested flag come back from
   `ParseArgs` as `OPT_UNKNOWN`.

4. **Unknown ⇒ the whole parse fails.** `lib/DxcSupport/HLSLOptions.cpp:534-537`
   loops over `Args.filtered(OPT_UNKNOWN)`, emits
   `Unknown argument: '<arg>'` and returns 1 — unless `-Qunused-arguments` is
   present, which is `Flags<[CoreOption]>` (`HLSLOptions.td:105`) and therefore
   *is* visible to the library. That is the switch the `*-qunused` cases use.

5. **Where `E_INVALIDARG` comes from.** `dxcutil.cpp:119-126`
   (`ReadOptsAndValidate`) builds an already-finished
   `DxcResult::Create(E_INVALIDARG, DXC_OUT_NONE, {ErrorOutput…})` and sets
   `finished = true`. Both entry points then hand that back and `return S_OK`:
   `dxcompilerobj.cpp:562-566` (`IDxcCompiler3`) and `:1908-1911`
   (`DxcCompilerAdapter::WrapCompile`, the legacy interface).

6. **The flag mask is only half the gap.** `-Fc` feeds `opts.AssemblyCode`
   (`HLSLOptions.cpp:619`), and that field has **no reader anywhere inside
   `tools/clang/tools/dxcompiler/`** — `git grep AssemblyCode` there exits 1,
   while the same pattern finds 10 hits repo-wide. The only code that *acts*
   on the value is `dxclib/dxc.cpp:378,438-439` (the driver) and the
   `dxc_batch` test tool. One further read exists in library-linked code —
   `HLSLOptions.cpp:1336` — but it only *rejects* a non-empty `AssemblyCode`
   when Metal codegen is on, and in the API path the field is always empty
   anyway, so that branch is unreachable there.

7. **No compile path produces a listing.** The sole producer of
   `DXC_OUT_DISASSEMBLY` is `DxcCompiler::Disassemble`
   (`dxcompilerobj.cpp:1386`); `:1813` is the legacy adapter *consuming* it.
   `include/dxc/dxcapi.h:381` documents precisely that:
   `DXC_OUT_DISASSEMBLY - Disassemble()`.

**So a PR that only adds `CoreOption` to `-Fc` would not implement this
issue.** It would stop the `E_INVALIDARG` and change nothing else: the value
would land in a field the library never reads, and no `Compile` path fills
`DXC_OUT_DISASSEMBLY`. That is the silent-failure outcome `expected.md` named
as the worst one for a caller, and it is worth saying out loud in the issue
because it is the obvious first patch to attempt.

The narrow shape a working PR needs: have `Compile` populate
`DXC_OUT_DISASSEMBLY` on the `IDxcResult` when asked, so one call yields both
the object and its listing — which is literally what the issue body asks for
("separate simultaneous disassembly output").

## The `-F*` family — the pattern is narrow

From `HLSLOptions.td:503-515` (probe 1 in the source-evidence file):

| option | flags | visible to the API? |
| --- | --- | --- |
| `-Fo` object | `CoreOption, RewriteOption, DriverOption` | yes |
| `-Fe` errors | `CoreOption, DriverOption` | yes |
| `-Fd` debug | `CoreOption, DriverOption` | yes |
| `-Fre` reflection | `CoreOption, DriverOption` | yes |
| `-Frs` root sig | `CoreOption, DriverOption` | yes |
| `-Fsh` hash | `CoreOption, DriverOption` | yes |
| `-Fi` preprocess | `CoreOption, DriverOption` | yes |
| **`-Fc`** listing | **`DriverOption`** | **no** |
| **`-Fh`** header | **`DriverOption`** | **no** |

`-Fc` and `-Fh` are the only two, and both are exactly the ones whose output
is a *derived text rendering* rather than a blob the compiler already has in
hand. That is an observable pattern, not evidence of intent. The issue's
feature-request wording and the 2024 maintainer comment are the evidence for
classifying it as an enhancement rather than a bug.

`variant-fre-*` and `variant-fh-*` are that table measured rather than read:
`-Fre` (a `CoreOption`) is accepted by both interfaces; `-Fh` (a
`DriverOption`) is rejected identically to `-Fc`. So the rejection is a
property of the flag mask, not of how the harness passes arguments.

## The documentation really is wrong (claim C)

The 2020 commenter wrote *"Documentation states that all options are
recognized by library calls"* and linked `docs/SPIR-V.rst`. That reading is
**correct**, not a misreading:

* `docs/SPIR-V.rst:4197-4198` — "Command-line options supported by SPIR-V
  CodeGen are listed below. They are also recognized by the library API calls."
* `docs/SPIR-V.rst:4211` — "``-Fc``: outputs SPIR-V disassembly to the given
  file"

Measured (`c1-spirv-*`, and the `spirv-fc` column of the release matrix): with
`-spirv`, `IDxcCompiler::Compile` rejects `-Fc` with the same
`Unknown argument: '-Fc'` / `E_INVALIDARG`, and with `-Qunused-arguments` it
compiles SPIR-V successfully and still produces no listing and no file. The
`-spirv` baseline in the same run succeeds, so this is not a build without
SPIR-V. `dxc.exe -spirv -Fc` *does* write the file (1228 bytes of SPIR-V
assembly, `manual-case-cmdline-vs-api.txt` section A2) — the promise is kept
on the command line and broken in the library.

That doc text predates the issue: the `-Fc` bullet is from `8702f97df`
(2017-10-20) and the "also recognized" sentence from `474954a6e` (2018-08-01).
It has misled at least one user for long enough to make them file a comment
saying so. Fixing the sentence is cheap and is worth doing **independently of
whether anyone implements the feature** — it is the part of this issue that
has a clear owner and no design question attached.

## Controls

| capture | what it rules out | expected | got |
| --- | --- | --- | --- |
| `variant-no-fc-*` | vacuity — every clause of `match.json` is trivially true of a run with no `-Fc` at all, except `fc-operand-seen=yes` | no-match | ✓ |
| `variant-joined-fc-*` | spelling sensitivity — `-Fc<file>` joined must behave as `-Fc <file>` separate | match | ✓ |
| `variant-fre-*` | "the harness passes arguments wrongly" — `-Fre` is a `CoreOption` and is accepted | no-match | ✓ |
| `variant-fh-*` | "only `-Fc` is special" — `-Fh` is `DriverOption` and is rejected identically | invalid-probe¹ | ✓ |
| `variant-cmdline-*` | "`dxc.exe` fails too" — the driver succeeds on the identical command line | no-match | ✓ |
| `variant-spirvdoc-no-fc-*` | vacuity of `match-spirv-doc.json` specifically | no-match | ✓ |
| `c1-baseline` (in-harness) | "the harness cannot compile anything" | object present | ✓ |
| `c1-disassemble` (in-harness) | "the harness cannot obtain disassembly at all" | 4104 bytes | ✓ |
| `c1-spirv-baseline` (in-harness) | "this DLL has no SPIR-V, so of course it fails" | object present | ✓ |

¹ `-Fh` is scored `invalid-probe` rather than `no-match` for two independent
and correct reasons: `triage.py`'s classifier treats `Unknown argument` as a
feature-absence marker (and this issue's symptom *is* that string), and `-Fh`
also poisons the harness's own `c1-baseline` anchor, tripping its
`PROBE-INCOMPLETE` guard. `--expect invalid-probe` is the honest declaration.
See `method-notes.md`.

The `c1-spirv-baseline` guard earned its keep. On **v1.4.1907 and v1.5.2003**
the `-spirv` cases return `0x80070057` — the *same* status as the `-Fc`
rejection — but for a completely different reason: `SPIR-V CodeGen not
available. Please recompile with -DENABLE_SPIRV_CODEGEN=ON.` Without the
baseline those two rows would have been reported as "SPIR-V rejects `-Fc`",
which is a false positive built from a true-looking status code. They are
reported as `no-spirv` instead.

## Release history

`manual-case-release-history.txt` — 21 releases + ground truth, every row a
full transcript. `c1-fc` is `0x80070057` in every row; `+Qunused` is `S_OK`
with `listing = none/obj` in every row; the `disasm` anchor is `present` in
every row. `IDxcCompiler3` is unavailable on v1.4.1907 only, so that row
measures the legacy interface alone — which is the interface the 2019 issue
and the 2020 comment were filed against, so the oldest row is also the most
directly relevant one. History: **`always-repro'd`**, with the first
measured point (2019-07-15) predating the issue (2019-11-26).

**`triage.py bisect` was deliberately not run.** It resolves a release tag to
that release's `dxc.exe` and builds its command line from `cmd.txt` — and
`dxc.exe` is the one caller that *does* handle `-Fc`. It would score every
release `no-repro` and report a confident "never repro'd in releases", the
exact opposite of the truth. Same trap as recorded on #2923 and #3237. The
matrix above replaces it and measures the right binary.

## Compiler Explorer

Skipped, reason recorded via `triage.py godbolt --issue 2604 --skip`. CE runs
`dxc.exe`, which is precisely the path that already works, and CE cannot call
the compile API at all — a link would demonstrate the opposite of the finding.
`manual-case-cmdline-vs-api.txt` is the local equivalent and shows both sides.

## Assessment

The issue is **valid, accurate as written, and unimplemented** — a genuine
feature request, not a bug. Nothing in six years and 21 releases has moved,
and the 2024 maintainer comment ("we'd happily review a PR … but we're not
planning on adding it") remains an accurate description of the state. The
issue text is not stale; `-Fc` still does exactly nothing in the compile API.

Suggested action **`enhancement-not-bug`**: keep it open, already labelled
`enhancement`. The triage value added here is three things a prospective
contributor cannot get from the thread:

1. the precise mechanism and file/line where the rejection is produced;
2. the warning that the one-line `CoreOption` patch is **not** the fix, and
   would convert a loud failure into a silent one;
3. the documentation defect in `docs/SPIR-V.rst`, which is separable,
   uncontroversial, and is what actually cost the 2020 commenter their time.

Labels: add **`api`** ("Issues related to compiler library API" — this is
exactly that, and the title's "Compile API" is currently unsearchable by
label) and **`up-for-grabs`** ("Contributors welcome" — the maintainer said so
in the thread in 2024 but no label records it). `docs` is *not* proposed for
this issue: the doc defect is real but is a distinct piece of work, and
hanging a `docs` label on a feature request would mis-file it. Better raised
separately; the evidence is in `manual-case-source-evidence.txt` probes 10-11.

Confidence: **high.** Ten cases, two interfaces, both codegen paths, 22
binaries spanning 2019-2026, six controls, and a source mechanism that
accounts for every observation exactly — including *why* `dxc.exe` differs and
*why* `-Fh` behaves the same.

## Re-running everything

    cd data/issues/2604
    ./build-fc2604.cmd                       # needs MSVC; finds vcvars itself
    python measure-2604.py --contrast --history --source

and through the harness:

    python scripts/triage.py run --issue 2604 --compiler main-debug-fc
    python scripts/triage.py run --issue 2604 --compiler main-debug-fc --match match-einvalidarg.json
    python scripts/triage.py run --issue 2604 --compiler main-debug-fc --match match-spirv-doc.json

Triaged with `13730886e`. (The ground-truth binary self-reports
`1.9.0.5433 (triage, ab5400907)`; that hash is a fork-local merge orphaned by
a history rewrite and resolves nowhere — its compiler sources are identical to
upstream `13730886e`, which is the commit to cite.)
