# #4723 — notes

**Verdict: `repros`.** The reported gap is real on the ground-truth build and on every
shipped release that has ever had `-MF`. But the interesting part is what was found next to
it: under `-P`, the `-M` family does not do *nothing*. It writes the dependency list into the
**preprocessed output file**, which silently corrupts it.

## What the issue asks for

Two sentences of prose, no repro, no version. The reporter uses `-M` (the flag added for
[#2063](https://github.com/microsoft/DirectXShaderCompiler/issues/2063)) to feed their build
system, also runs a separate preprocess-to-file step, and wants dependency output from that
step too. Decomposed in `expected.md` as three asks:

| ask | measured |
| --- | --- |
| A1 `-MF <file>` writes a depfile when `-P` is on the command line | **no** |
| A2 `-MD` writes `<input>.d` when `-P` is on the command line | **no** |
| A3 the preprocessed output itself is unaffected | **no — it is corrupted** |

A3 was written down before running anything, as the control for "did the flag break something
else?". It is the one that failed most interestingly.

**Scored against the rule in `expected.md`, not one invented afterwards.** That file
pre-committed: *"Reproduces = case 3 fails to produce the depfile while case 2 produces it"*,
and reserved `changed-behavior` for "the depfile is written but the preprocessed output is
dropped (or vice versa)". Measured: no depfile, preprocessed output present. That is `repros`
by the pre-committed definition. The corruption is a *third* outcome the decision rule did not
anticipate — neither artifact is dropped, one is silently spoiled — so it is recorded as a
separate finding with its own predicate (`match-contamination.json`) rather than by quietly
restating the status to fit it.

## Measurement

`cmd.txt` is seven invocations: three A/B pairs (`-MF`, `-MD`, `-M`, each with and without
`-P -Fi …`), then a seventh that feeds the `.i` from pair 1 back to `dxc`. The observable is
which files a run wrote, which stdout cannot show, so the registered "compiler" is
`run-dep4723.cmd` → `dep4723.py`, a harness that clears the expected artifacts, runs `dxc`,
and reports what appeared. Per SKILL.md's rule for symptoms `dxc.exe` cannot put in a capture.

Absence is reported as a **positive** line (`dep4723-artifact depfile-MF dep-preprocess.d
MISSING`), emitted only after the harness has parsed the command line and looked at the
filesystem, and every finding clause is anchored on the adjacent line proving the same
invocation *did* write its preprocessed output. A run that never started cannot satisfy the
predicate; a `not_contains` clause would have been satisfied by one.

### The finding, from `out-main-debug-dep4723.txt`

```
$ dxc -T ps_6_0 -E main -MF dep-compile.d repro.hlsl
dep4723-artifact depfile-MF dep-compile.d PRESENT bytes=63
dep4723-content dep-compile.d | repro.hlsl: repro.hlsl \

$ dxc -T ps_6_0 -E main -P -Fi repro.i -MF dep-preprocess.d repro.hlsl
dep4723-artifact depfile-MF dep-preprocess.d MISSING
dep4723-artifact preprocessed-P repro.i PRESENT bytes=354
dep4723-tail repro.i | repro.hlsl: repro.hlsl \
dep4723-tail repro.i |  inc/common.hlsli \
dep4723-tail repro.i |  inc/nested.hlsli
```

The same 63 bytes that `-MF` writes to a depfile in compile mode are, under `-P`, appended to
the end of the preprocessed output instead. `-MD` and `-M` behave identically.

### The consequence

```
$ dxc -T ps_6_0 -E main repro.i
repro.hlsl:9:1: error: unknown type name 'repro'
repro.hlsl: repro.hlsl \
^
dep4723-exit=0x80004005
```

`0x80004005` is `E_FAIL`, an ordinary diagnosed error, not a crash. A build that preprocesses
to file and compiles the result — exactly the workflow the issue describes — gets a broken
`.i` the moment it adds `-M` to the same command line. Nothing warns.

### Controls

| control | predicate | expect | got |
| --- | --- | --- | --- |
| `control-compile-mf` — same command minus `-P -Fi` | `match-depmissing` | no-match | no-repro |
| `control-p-only` — same command minus `-MF` | `match-depmissing` | no-match | no-repro |
| `control-p-only` — same command minus `-MF` | `match-contamination` | no-match | no-repro |
| `subject-mf-p` — the `-P` line alone | `match-depmissing` | match | repro |
| `noinclude` — a shader with no `#include` | `match-depmissing` | match | repro |

`control-p-only` against `match-contamination.json` is the strongest single artifact in the
directory. Identical command, one flag removed:

```
with -MF:     repro.i 354 bytes, tail = "repro.hlsl: repro.hlsl \"
without -MF:  repro.i 291 bytes, tail = "float4 main(float4 pos : SV_Position) : SV_Target {"
```

The depfile flag is the cause, and `-P` on its own is fine.

### Was the flag even parsed?

Exit status is worthless here — all six invocations exit 0, and so does `/ZZZNONSENSE`, because
dxc silently ignores unknown `/`-style flags. `manual-case-flag-parse-proof.txt` settles it a
different way, by making the flag fail:

```
$ dxc -T ps_6_0 -E main -MF no-such-dir/dep.d repro.hlsl
exit=0x00000001
| The system cannot find the path specified. no-such-dir/dep.d

$ dxc -T ps_6_0 -E main -P -Fi parse-proof.i -MF no-such-dir/dep.d repro.hlsl
exit=0x00000000
| (no output)
```

Character-for-character the same `-MF` argument. Compile mode parses it and tries to open the
file; `-P` mode accepts it and never asks anyone to open anything. That is a routing gap, not
an unrecognised option — and `-help` lists all three flags, so they are not fictional.

The same file records the contrast that decides how to label this: `-Fo` under `-P` **does**
produce `warning: compiler options ignored with Preprocess.` The machinery to tell the user an
output flag is inert in this mode already exists; `-M`/`-MD`/`-MF` were left off the list.

## Mechanism (read-only source reading, no DXC source was modified)

Two independent causes, one per symptom.

1. **No depfile.** `DxcContext::Preprocess()` (`tools/clang/tools/dxclib/dxc.cpp:1005-1039`)
   calls `IDxcCompiler::Preprocess` and writes the whole result blob to the `-Fi` file. Every
   depfile is written by `DxcContext::ActOnBlob()` (`dxc.cpp:300-322`), which the `-P` path
   never reaches. `-MD`/`-MF` are therefore unreachable in this mode by construction.
2. **Corrupted `.i`.** In `DxcCompilerObj::Compile`
   (`tools/clang/tools/dxcompiler/dxcompilerobj.cpp`), `if (isPreprocessing)` runs
   `PrintPreprocessedAction` into `outStream` (lines 721-740) and then, as a *sibling*
   statement rather than an `else`, `else if (opts.DumpDependencies)` writes the make rule into
   the **same** `outStream` (lines 870-894). Both land in one result blob. Nothing suppresses
   the second when the first ran.

The missing diagnostic is a third, smaller thing:
`lib/DxcSupport/HLSLOptions.cpp:980-992` warns "compiler options ignored with Preprocess" for
`Fh/Fo/Fe/Fre/Frs/Fsh` only — the `-M` family is absent from that list.

The minimum viable fix is one line in that list. The fix the issue actually asks for is to
route dependency output in the `-P` path.

## History — `always-repro'd`

`bisect` refuses to drive a harness (`refuse_harness_bisect`), correctly, so
`measure-history.py` walks the cached releases directly with the same measurement and two
positive controls per release. Prereleases excluded: the issue names no version.
Full matrix in `manual-case-release-history.txt`.

| releases | result |
| --- | --- |
| v1.4.1907 … v1.6.2112 | **invalid probes** — no `-MF` in compile mode at all; the flag family postdates them (#2063 closed 2021-12-21) |
| v1.7.2207 (current when this was filed) … v1.9.2607, ground truth | depfile under `-P`: MISSING; preprocessed output: CONTAMINATED; recompiles: no (0x80004005) |

Identical byte counts — 354 with `-MF`, 291 without — on every release from v1.7.2207 to
today. Never worked, never regressed, unchanged for the entire life of the issue.

**`-P` did change inside the window, and it does not matter.** `8bf2b087c` (PR #4624, first
shipped in v1.7.2212) turned `-P` from a Separate option taking the output filename into a
flag paired with `-Fi`; `054e0f507` (v1.9.2607) renamed the fxc-style spelling to `/Po`. The
history sweep probes both spellings on every release and records which one worked — v1.7.2207
needs the old one, everything later the new one — and the behaviour under test is the same on
both sides of the change. So the report's description of `-P` is still accurate today.

## Why not `enhancement-not-bug`

That was the expected shape going in, and it is wrong. Three reasons, in increasing order of
weight:

1. Both halves of the feature already exist and work; only the combination is broken.
2. The combination is not unimplemented, it is half-implemented — the dependency list is
   computed and emitted, just into the wrong file.
3. The result is silent corruption of a file the user asked for. A build that adds `-M` to its
   existing `-P` step gets a `.i` that no longer compiles, with no diagnostic and exit 0.

(3) is a bug on any reading, which is also why the existing `bug` label is right and
`enhancement` would be misleading.

## Related

- [#5416](https://github.com/microsoft/DirectXShaderCompiler/issues/5416) — `-MD -MF` during
  *compilation* writes the `.d` but no `.cso`, silently. Same subsystem, same "one output
  displaces the other" shape, opposite direction. Filed as "definitely related to #4723" and
  it is: a fix that routes dependency output as a separate stream rather than through the main
  output stream would address both.
- [#3863](https://github.com/microsoft/DirectXShaderCompiler/issues/3863) — `-H` and `-P`
  together, i.e. the same "second output flag under `-P`" family.
- [#2063](https://github.com/microsoft/DirectXShaderCompiler/issues/2063) — where `-M` came
  from; closed 2021-12-21.

Not a duplicate of any of them. #5416 is the compile-mode case and this is the preprocess-mode
case; a maintainer may reasonably want to fix them together.

## Not measured

- **Whether `dxcompiler.dll` consumers see this.** Everything here is through `dxc.exe`. The
  corruption is inside the compiler object rather than the driver, so an API caller passing
  `-P` and `-M` together should get the same contaminated blob, but that was not run.
- **`-MT`/`-MJ` or other depfile-adjacent flags**, if any exist; only the three the issue
  names were probed.
- **Whether the reporter's build actually hits the corruption.** They may pass `-M` and `-P` in
  separate invocations, in which case only the missing feature affects them. Nothing in the
  issue says which.
