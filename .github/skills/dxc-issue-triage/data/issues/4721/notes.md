# Issue 4721 — notes

**"Support applying clang fix-its automatically"** — filed 2022-10-12 by
llvm-beanz, label `hlsl-next`, open. Three asks:

1. `-fixit` — apply fix-its, overwriting the input.
2. `-fixit=<ext>` — apply them to a new file with the given extension.
3. Apply fix-its automatically in the HLSL rewriters.

This is a feature request, not a bug report, so "does it still reproduce" is
the wrong question. The measurable question is **how much of the capability
already exists and where the gap actually is** — and that turned out to have a
sharp answer.

Ground truth: `main-debug` = `build/Debug/bin/dxc.exe`, registered at commit
`13730886e6a9019e4e0823746470f3ab75341d6b`. (`--version` self-reports
`1.9.0.5433 (triage, ab5400907)`, an older snapshot id than the registry
records; the registered commit is cited, per SKILL.) Rewriter probes use
`build/Debug/bin/dxr.exe` from the same build.

## The finding in one line

DXC already computes the fix, and already prints it, and has no way to apply
it — while the same fix-it machinery, in the same lineage, is fully working
one fork over.

## What was measured

### The flag does not exist, and never has

`out-main-debug.txt` runs the two `cmd.txt` lines against one compiler:

```
$ dxc -T ps_6_0 -E main -HV 2021 -fixit repro.hlsl
dxc failed : Unknown argument: '-fixit'
```

…and, immediately below, the same compiler on the same file without the flag:

```
repro.hlsl:12:18: error: operands for short-circuiting logical binary operator must be scalar, for non-scalar types use 'and'
  bool4 mask = a && b;
               ~~^~~~
               and(a, b)
```

That second block **is** a clang `FixItHint`, rendered. `and(a, b)` is not
prose: it is the corrected source text, positioned under the range it
replaces. `control-fixed.hlsl` is that suggestion pasted in, and it compiles
clean — so the fix DXC declines to apply is a complete and correct one.

`-fixit=hlsl`, `-fixit-recompile` and `-Xclang` are rejected the same way —
nonzero exit, no object written (`manual-case-flag-spellings.txt`, and
`variant-xclang-main-debug--match-xclang.txt` for the scored `-Xclang` case).
There is no escape hatch: `dxc -help` (204 lines) contains none of `fixit`,
`fix-it` or `Xclang`, and the same search does find `Qembed_debug`, so it is a
search that can find things.

Across **20 stable releases** v1.4.1907 → v1.9.2607 plus the local build,
`-fixit` is rejected every time and `repro.hlsl` is byte-identical before and
after every run (`manual-case-release-matrix.txt`; the hash column exists
because a working `-fixit` would rewrite its own input, and a probe that
destroys its evidence looks exactly like a probe that found nothing).
`bisect --linear --match match-flag.json` agrees: rejected on all 20.

### `/fixit` is not "accepted" — it is discarded

`dxc /fixit shader.hlsl` exits **0**. That is the trap, not a result: dxc
silently drops unrecognised `/`-prefixed arguments, so a clean exit is
indistinguishable from success. `manual-case-flag-spellings.txt` settles it by
byte identity of the compiled object rather than by exit code:

| case | object sha256 | meaning |
| --- | --- | --- |
| baseline (no flag) | *X* | — |
| `/fixit` | *X* | changed nothing |
| `/ZZZNONSENSE` | *X* | changed nothing |
| `-Zi -Qembed_debug` | ≠ *X* | **instrument self-test**: an honoured flag *does* move the hash |
| `-fixit` | no object | parsed, and rejected |

Without that fourth row the first three prove nothing — three identical hashes
are equally consistent with a blind instrument.

### The hint predates the request

Only one probeable release renders no hint: **v1.6.2112** diagnoses the same
line with a bare caret and no suggested replacement. From **v1.7.2207** onward
every release prints `and(a, b)`. So the fix-it hints arrived between Dec 2021
and Jul 2022 — *before* this issue was filed in Oct 2022 — which fits the
issue: it asks to apply hints that already existed, not to invent them.

Releases v1.4.1907 → v1.6.2106 answer `Unknown HLSL version: 2021` and are
**not evidence** about hint rendering; the matrix's column (c) marks them
`no-HLSL-2021` for exactly that reason.

### The machinery is present in this tree but unreachable

Read-only source corroboration, all in this repo:

| what | where |
| --- | --- |
| the rewriter itself | `tools/clang/lib/Frontend/Rewrite/FixItRewriter.cpp` (built into `clangRewriteFrontend`) |
| the frontend action | `tools/clang/lib/FrontendTool/ExecuteCompilerInvocation.cpp:53` — `case FixIt: return new FixItAction();` |
| the cc1 flags | `tools/clang/include/clang/Driver/CC1Options.td:396,398` — `-fixit`, `-fixit=<value>` |
| flag → action | `tools/clang/lib/Frontend/CompilerInvocation.cpp:868` → `frontend::FixIt` |
| already linked in | `tools/clang/tools/dxcompiler/CMakeLists.txt:91` links `clangRewriteFrontend` |
| hints attached by HLSL Sema | `tools/clang/lib/Sema/SemaHLSL.cpp:10713, 11039` — `FixItHint::CreateReplacement` |
| hint rendering on by default | `tools/clang/include/clang/Basic/DiagnosticOptions.def:56` — `ShowFixits` = 1 |
| **the gap** | `include/dxc/Support/HLSLOptions.td` — the dxc driver option table defines neither `fixit` nor `Xclang` |

Nothing under `tools/clang/tools/dxcompiler/` mentions `FixIt`, `ProgramAction`
or `CreateFromArgs`: the cc1 path that would select `FixItAction` is not
constructed by the dxc entry point at all. `clang.exe`, which *does* have
`-cc1`, is `EXCLUDE_FROM_ALL` in this repo and is not in the default build.

### The same machinery works, today, one fork over

`manual-case-clang-fixit.txt` — four Compiler Explorer runs, two of them
controls. `hlsl_clang_trunk` is llvm-project clang in DXC driver mode, so it
has `-Xclang`:

```
# hlsl_clang_trunk, control-generic-fixit.hlsl, -Xclang -fixit
<source>:12:17: error: expected ';' at end of declaration
   12 |   float4 v = 1.0
      |                 ^
      |                 ;
<source>:12:17: note: FIX-IT applied suggested code changes
```

The same file, same compiler, **without** the flag prints the identical error
and no `FIX-IT` line — so the marker is evidence about the flag and not about
the diagnostic. `dxc_trunk` given those flags answers
`dxc failed : Unknown argument: '-Xclang'`.

The rewriter is not missing from the lineage. It is missing from **this
fork's driver surface**. That shrinks the request from "implement fix-it
application" to "route the driver to a frontend action that is already
compiled into `dxcompiler`" — the same shape as the forced-include finding
elsewhere in this batch, except that here even the `-Xclang` escape hatch is
absent, so there is no workaround at all for a dxc user.

One caveat, and it is a design input rather than a nitpick: on the issue's own
repro clang says `note: FIX-IT detected an error it cannot fix`, because clang
attaches the suggestion to a follow-on `note:` rather than to the error. DXC
attaches its hint to the error itself (`SemaHLSL.cpp:10713`), which is the
placement a rewriter needs. So DXC's hints are, if anything, better positioned
for this feature than clang's are.

### Ask 3: the rewriters do not apply fix-its either

`dxr.exe -E main -HV 2021 repro.hlsl` (`variant-rewriter-*`):

- prints the diagnostic **and** the `and(a, b)` hint,
- exits **0**,
- and emits `bool4 mask;` — the rewritten output omits the diagnosed
  initializer (under dxr's default "unchanged" rewrite mode, i.e. the mode
  that alters least).

The control (`control-fixed.hlsl`, same command) preserves
`bool4 mask = and(a, b);`, so the omission is caused by the error, not by the
rewriter discarding initializers generally. The error and hint *are* printed,
so this is not silent to a reader of stderr — but the return code is 0 and the
emitted rewrite carries no marker, so a caller that checks the exit status
gets a truncated shader and no signal. On this repro the rewriter's response
to a fixable diagnostic is to drop the code the diagnostic points at. I did
not test other diagnostics, so I state it as an observation about this case
rather than about the rewriter in general; it looks like a separate defect.

## Incidental finding, recorded because it bears on the design

Matrix column (d) asks whether the replacement DXC suggests is one DXC can
compile. On **v1.7.2207 → v1.8.2407** — ten releases, over two years — it is
not: `and(a, b)` compiles to

```
error: validation errors
Invalid record
```

and column (e) re-runs it with `-Vd`, where it still fails
(`error: Invalid record`) — so it is the compiler rejecting its own output
rather than a validator-signing mismatch. A one-variable narrowing
(`bool4 m = a > b` compiles; anything using `and()` does not) points at the
intrinsic. Fixed by v1.8.2502.

This is out of scope for 4721 and I did not chase it further, but it bears on
the feature: a `-fixit` shipped in that window would have rewritten users'
sources into code that release could not compile. Whether that argues for or
against the feature is a maintainer call; the measurable part is that an
applied fix-it can be tested and a printed one cannot.

## Proposed labels

Current: `hlsl-next`. Proposed additions, each with the evidence it rests on:

- **`enhancement`** ("Feature suggestion") — the issue requests capability
  that has never existed; nothing is claimed broken. This is the routing label
  the taxonomy provides for that, and it is currently absent.
- **`diagnostic`** ("Issues for diagnostics") — the whole feature lives in the
  diagnostics pipeline: `FixItHint`s attached in `SemaHLSL.cpp`, rendered by
  the diagnostic printer (`ShowFixits`), consumed by `FixItRewriter`.
- **`rewriter`** ("Bugs in the rewriter") — ask 3 is explicitly about the HLSL
  rewriters, and the `dxr` measurement above is a rewriter-scoped finding.

No removals proposed. `hlsl-next` is a slightly odd fit for tooling rather
than language work, but the reporter's own follow-up ties it to HLSL 202x
adoption ("to aid developers in adopting new syntaxes to replace removed
ones"), so the association comes from the issue itself.

## Scoring the prediction in `expected.md`

`expected.md` was written before any measurement and predicted only that
`-fixit`, `-fixit=<suffix>` and `/fixit` would all be unavailable, explicitly
declining to guess Q1–Q4. Scored:

| # | question | prediction | measured |
| --- | --- | --- | --- |
| — | the three flag spellings unavailable | unavailable | **correct** |
| Q1 | does Sema attach and render hints? | not guessed | **yes**, since v1.7.2207 |
| Q2 | is `FixItRewriter`/`FixItAction` still in the tree? | not guessed | **yes**, and linked into `dxcompiler` |
| Q3 | is any spelling reachable? | not guessed | **no** — not even `-Xclang` |
| Q4 | do the rewriters apply fix-its? | not guessed | **no**, and `dxr` drops the code instead |

The shape declared in advance — `enhancement-not-bug`, history
`never-implemented`, not `always-repro'd` — survives measurement. Q3 is the
one that came out *worse* than the comparable forced-include case in this
batch: there, `-Xclang` provided a workaround; here there is none.

`expected.md` also warned that the Clang-based HLSL front end "is a separate
compiler; if it has the capability that is evidence about the successor, not
about DXC". That caveat stands and is why the CE clang result is reported as
evidence about the *lineage and the shape of the work*, not as evidence that
this tree's copy is functional.

## What I could not measure

- **That the inherited `-cc1 -fixit` path works when built from this tree.**
  It would need building the optional `clang.exe` target, which writes outside
  the issue directory and could relink binaries other concurrent workers are
  using. Not attempted; recorded in `method-notes.md`. It would upgrade "the
  code is present and linked in" to "the code is present, linked in, and
  functional here" — the CE clang result is strong evidence for the lineage
  but is a *different* build of a *different* fork.
- **Whether `tools/clang/test/FixIt/` runs in DXC's lit suite.** The tests are
  present and use `%clang_cc1 -fixit`; I established only that `clang.exe` is
  not built by default.
- **Ask 2's exact semantics** (`-fixit=<ext>` writing a sibling file) is
  untestable while ask 1's flag does not parse.
- **Anything about `/`-style spellings on Compiler Explorer**: CE's Linux
  builds read a leading `/` as a path, so MSVC-style flags cannot be tested
  there at all. That is why the `/fixit` evidence is local and hash-based.
