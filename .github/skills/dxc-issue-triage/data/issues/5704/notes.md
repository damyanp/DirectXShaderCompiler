# Issue 5704: Linker doesn't strip resource names when using -Qstrip_reflect

## Repro quality: complete

Filed with a full C++ repro (`IDxcCompiler3`/`IDxcLinker`): compile a
compute-like HLSL function to `lib_6_3` with `-Qstrip_reflect`, link to
`cs_6_3` with `-Qstrip_reflect`, disassemble, and observe that
`texResource`/`rwTexResource` still appear in the linked disassembly despite
the strip flag. See `expected.md` for the pre-registered symptom definition.

The reporter's function (`repro.hlsl`) has no `[shader(...)]` attribute --
just `[numthreads(8,8,1)]` and a `-E main` match. dxc warns
`attribute 'numthreads' ignored without accompanying shader attribute` but
the reporter's own dxc (1.7.2308) still compiled and linked it as if it were
the entry point. That detail turns out to matter (see "A second, unrelated
regression" below).

## CLI reconstruction

There is no single `dxc` invocation equivalent to the reporter's API
sequence; `cmd.txt` is the 3-line pipeline: compile `repro.hlsl` to
`lib_6_3` (`-Qstrip_reflect -O3 -Fo lib.bc`), `-link lib.bc -T cs_6_3
-E main -Qstrip_reflect -O3 -Fo linked.bc`, then `-dumpbin linked.bc`.
`match.json` looks for `\btexResource\b` / `\brwTexResource\b` anywhere in
the combined output (the defect as reported). `match-nolink.json` tracks a
separate signature, "Cannot find definition of function main" from the link
step, needed to tell a genuine fix apart from a probe that never completed
the pipeline (see below).

## The reported defect is real, and reproduces on the reporter's own version

Run directly against the historical v1.7.2308 release binary (cached at
`build/tools/clang/test/dxc_releases/v1.7.2308/dxc_2023_08_14/bin/x64/dxc.exe`),
the literal repro compiles, links, and the linked disassembly leaks both
`texResource` and `rwTexResource` through `-Qstrip_reflect`, exactly as
reported.

## A second, unrelated regression: the literal repro can no longer link at all

On current `main-debug` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df), the
literal repro's `-T lib_6_3` compile now produces an **empty module** (the
`numthreads`-only function has no `[shader(...)]` attribute, so it gets
`internal` linkage and is dead-code-eliminated at the initial compile step --
confirmed with `-fcgl`, which shows the function present with `internal`
linkage in the pre-finalization HL IR, and absent from the finalized/lowered
`lib_6_3` output regardless of `-O3`/`-Od`/no `-O` flag). The subsequent
`-link ... -E main` step then fails: `error: Cannot find definition of
function main`. This is a change in the numbered-library (`lib_6_3`) default
linkage/export-recognition rules, not a fix or a symptom of the reported
defect; `SemaHLSLDiagnoseTU.cpp`'s `IsTargetProfileLib6x` /
`getDefaultLinkageExternal` and `CGHLSLMS.cpp`'s `SetDefaultLinkage` govern
this (the latter predates the issue by years and is not itself the change;
the former was added by commit 48842f99e, 2023-11-16, after the issue was
filed, but governs diagnostics reachability, not the codegen decision itself
-- the exact commit that stopped keeping an unattributed, `-E`-matching
function in a `lib_6_3` compile was not identified).

Because this failure means `linked.bc` is never written, the pipeline's own
`-dumpbin linked.bc` line has nothing of its own to disassemble.

## Isolating the actual reported defect: `repro-shader-attr.hlsl`

Adding `[shader("compute")]` to the reporter's function (making it a properly
exported library entry point, which the current front end requires
regardless of the strip_reflect question) lets the full pipeline complete.
This isolates the reported defect from the linkage regression above and is
the only way to test the actual question ("does -Qstrip_reflect strip names
across a lib->link boundary") on any release from v1.8.2403 onward, where the
literal repro can no longer even reach that code path.

Control: direct (non-library) `cs_6_0`/`cs_6_3` compiles with
`-Qstrip_reflect` strip cleanly on both old and current builds -- confirms
the predicate discriminates the library/link path specifically, and is not
just matching everything.

## Corrected release history (see "Evidence corruption" below for why the
## original `bisect` capture must be disregarded)

`measure.py` and `measure-variant.py` re-measure both repros against every
catalogued stable release that accepts `-link` (v1.6.2106 onward), each in a
freshly created and freshly deleted per-release scratch directory, and
record a release as `invalid-probe` whenever its own `-link` step failed to
produce `linked.bc`, rather than falling through to disassembling whatever is
already on disk. Full output: `manual-case-release-history.txt` (literal
repro) and `manual-case-shader-attr-history.txt` (shader-attributed variant).

Literal repro (`manual-case-release-history.txt`):

| release | result |
| --- | --- |
| v1.6.2106 .. v1.7.2308 | `repro` -- names leak |
| v1.8.2403 onward (incl. main-debug) | `invalid-probe` -- link fails, unrelated regression above |

Shader-attributed variant, isolating the actual reported defect
(`manual-case-shader-attr-history.txt`):

| release | result |
| --- | --- |
| v1.6.2106, v1.7.2308 | `repro` -- names leak |
| v1.8.2403, v1.8.2505, v1.9.2607, main-debug | `no-repro` -- names correctly stripped |

**The reported defect is fixed between v1.7.2308 (2023-08-14) and v1.8.2403
(2024-03-07).** No stable release exists in the catalog between these two
tags (the next entries are pre-releases, out of policy scope for this issue,
which names none of them), so this is the narrowest boundary obtainable from
stable releases; the window spans roughly seven months of `main` history and
was not narrowed to a single commit (that would require building intermediate
commits, out of scope for read-only, no-rebuild triage). Call the fix
attribution to "somewhere in this window" strong, not certain: it rests on
one release either side of a genuine transition, not on a bisected commit.

Confidence: high that (a) the defect reproduced as filed against v1.7.2308,
and (b) the same underlying mechanism is fixed by v1.8.2403 when tested with
a currently-valid equivalent input. Lower confidence on the literal repro's
own fate through that same window, since it stopped being a valid probe at
the same boundary -- it is unmeasurable, not fixed, for that specific input
shape from v1.8.2403 onward.

## Evidence corruption discovered during bisection: the original `triage.py
## bisect` capture for this issue is not trustworthy

Full account in `method-notes.md`. Summary: `run`/`bisect`'s normal probe
path (`_run_command_list`, not the isolated-scratch-copy path used only for
spelling retries) executes every line of `cmd.txt` with the issue directory
itself as `cwd`, so `lib.bc`/`linked.bc` are shared filenames across every
release probed in one sweep. dxc only writes `-Fo` output on success, so a
release whose own `-link` step fails leaves an *earlier* release's
`linked.bc` on disk, and the following `-dumpbin linked.bc` line
disassembles that stale file instead of reporting the failure.

Measured directly: `out-v1.6.2106.txt` (link exit 0) and `out-v1.9.2607.txt`
(link exit 1, "Cannot find definition of function main") were captured in
the same sweep at the identical timestamp, and both `-dumpbin` outputs carry
the identical embedded shader hash `7023918e6966b36ebde405470921951d` and
identical `"clang version 3.7 (tags/RELEASE_370/final)"` identification
string -- byte-identical DXIL, despite v1.9.2607's own link having failed two
lines earlier in the same capture. v1.9.2607's `-dumpbin` never touched its
own output. Both files are kept unmodified as the evidence of this trap;
they must not be read as history for this issue. `measure.py` /
`measure-variant.py` (see above) are the trustworthy replacement.

## What this means for the issue

Two separate findings, not one:

1. The reported symptom (resource names leaking through `-Qstrip_reflect`
   across a `lib_6_3` -> linked `cs_6_3` boundary) reproduced exactly as
   filed against the reporter's own v1.7.2308, and is fixed as of v1.8.2403
   when the same construct is expressed the way the current front end
   requires (`[shader("compute")]` on the entry point).
2. Separately, and apparently in the same release window, the *literal*
   as-filed repro (no `[shader(...)]` attribute) stopped being able to link
   at all -- a distinct, unreported regression in how `lib_6_3` treats an
   unattributed, `-E`-matching function. Whether this is itself a defect
   worth its own issue is outside this triage's scope, but it means nobody
   re-running the reporter's exact repro today will see either the original
   symptom or a clean pass; they will see a new and different failure.

Godbolt: skipped (`godbolt --skip`) -- the repro is an inherently multi-step
compile/link/disassemble pipeline that Compiler Explorer, which has no
linker stage, cannot express in a single pane.

Labels: current (`bug`, `reflection`, `shader-linking`) remain accurate;
`labels --issue 5704` proposes no changes.
