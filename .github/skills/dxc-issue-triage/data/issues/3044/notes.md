# Issue 3044 — "Feature request: option to preprocess without removing comments"

Opened 2020-07-16 by `jeffnn`. Label: `enhancement`. The title is the whole
request: the body is empty. One comment, 2020-09-25, by `pow2clk`
(COLLABORATOR): *"This is something that clang provides with the `-CC` flag.
Presumably we can add it without too much difficulty."*

No maintainer has stated a design objection, and nobody posted a workaround.
The GitHub timeline for #3044 has no cross-reference events at all, so nothing
in the repository claims to have implemented or superseded this.

## Verdict in one line

Still valid, still unimplemented, and — the useful part — **the capability is
already in the library; only the driver-side plumbing is missing.** Two
hardcoded constants and one option-table entry stand between DXC and this
request. That turns an open-ended feature request into a bounded
option-plumbing task.

## What was measured

Repro quality in the issue itself: **none** — there is no repro, no command
line, and no body text. Everything below is agent-constructed.

`repro.hlsl` is a pixel shader in which the sentinel `keepme3044` appears
**only inside comments** (a line comment, a block comment, a block comment
inside `main`, and a trailing comment). `selftest3044` and `macroexpanded3044`
are code identifiers, and `EXPANDED3044` is a macro, so a real preprocess
produces the line

    return selftest3044 + macroexpanded3044;

which does not exist anywhere in the input. `control-token-in-code.hlsl` is
the same shader with one difference: it also declares
`static const int keepme3044 = 3;` and uses it, so the sentinel is a code
identifier there too.

`dxc -P` never writes to stdout — it writes the preprocessed text to `-Fi`, or
to `<input>.i` (`tools/clang/tools/dxclib/dxc.cpp`, `WriteBlobToFile`). So
`cmd.txt` is a four-step chain: preprocess each shader to a `.i`, then compile
each `.i` with `-Zi` so DXC embeds the preprocessed text in `!dx.source.contents`
where a predicate can read it on stdout.

Measured on `main-debug` (a clean Debug build of this tree, self-reporting
`1.9.0.5433`; source-identical to upstream `13730886e`):

    !28 = !{!"preprocessed.i", !"#line 1 \22repro.hlsl\22 ...
              static const int selftest3044 = 1;
              static const int macroexpanded3044 = 2;
              float4 main() : SV_Target {
                return selftest3044 + macroexpanded3044;

    !30 = !{!"control-token-in-code.i", !"#line 1 \22control-token-in-code.hlsl\22 ...
              static const int selftest3044 = 1;
              static const int macroexpanded3044 = 2;
              static const int keepme3044 = 3;

The macro expanded, so preprocessing genuinely ran; the control's `.i` contains
`keepme3044`, so the search is not dead; and the repro's `.i` does not. Comments
are dropped. `match.json` asserts all four facts together plus the exit status
of the preprocess step of *this* run, so it cannot be satisfied by a stale file
or by a compile that emitted nothing.

## Is there a flag today?

No. Both clang spellings are rejected outright:

    $ dxc -P repro.hlsl -Fi flag-probe.i -C
    dxc failed : Unknown argument: '-C'          (exit 1)

    $ dxc -P repro.hlsl -Fi flag-probe.i -CC
    dxc failed : Unknown argument: '-CC'         (exit 1)

The `/` spellings must not be read as acceptance. `dxc` does not diagnose an
unrecognised `/x`; it falls through to the input list, so when it is placed
before the real input it is simply swallowed:

    $ dxc -P /C repro.hlsl -Fi flag-probe.i          exit 0, no diagnostic
    $ dxc -P /CC repro.hlsl -Fi flag-probe.i         exit 0, no diagnostic
    $ dxc -P /ZZZNONSENSE repro.hlsl -Fi flag-probe.i exit 0, no diagnostic

All three produce output byte-identical (same SHA-256) to a run with no flag at
all — including `/ZZZNONSENSE`, which is the control for "silently ignored".
So `/C` did nothing; it was not parsed. This is measured at every release in
`manual-case-release-history.txt`.

Negative control: `-P missing3044.hlsl -Fi preprocessed.i` exits 1 with *"The
system cannot find the file specified"* and is scored **no-repro** by
`match.json` — the absence clause alone is not enough to satisfy the predicate.

## Where the capability already is

- `tools/clang/include/clang/Frontend/PreprocessorOutputOptions.h` declares
  `ShowComments` and `ShowMacroComments`.
- `tools/clang/lib/Frontend/PrintPreprocessedOutput.cpp:744` honours them:
  `PP.SetCommentRetentionState(Opts.ShowComments, Opts.ShowMacroComments);`
- `tools/clang/lib/Frontend/CompilerInvocation.cpp:1870,1872` parses `-C` and
  `-CC` into those fields — but inside `ParsePreprocessorOutputArgs`, reached
  only from `CompilerInvocation::CreateFromArgs`, i.e. the `cc1` path. The dxc
  driver never goes through it.
- `tools/clang/tools/dxcompiler/dxcompilerobj.cpp:721-733` builds
  `PreprocessorOutputOptions` by hand instead, and hardcodes:

      // These settings are back-compatible with fxc.
      PPOutOpts.ShowComments = 0;      // Show comments.
      PPOutOpts.ShowMacroComments = 0; // Show comments, even in macros.

- `include/dxc/Support/HLSLOptions.td` has no `C` or `CC` option. (`Cc` at
  line 520 is unrelated — "Output color coded assembly listings".)
- `tools/clang/tools/libclang/dxcrewriteunused.cpp:1135,1138` hardcodes the
  same two zeros for the rewriter, so a fix should decide whether it applies
  there too.

So `pow2clk`'s 2020 assessment holds up: the work is an option-table entry, the
plumbing from `DxcOpts` into those two fields, and tests. The `fxc`
back-compatibility comment explains why the default must stay `0`.

## Release history

At the time of triage, generic `triage.py bisect` was unsafe here: its automatic
spelling retry silently overwrote `repro.hlsl` on releases up to v1.7.2207.
Batch 012 changed the runner to isolate every attempt and refuse input mutation,
so that failure now hard-errors without touching the evidence. Generic bisection
still cannot represent both historical `-P` grammars, so history remains the
explicit grammar-aware matrix,
`manual-case-release-history.py` → `.txt`, over all 20 stable releases plus
`main-debug`.

Result, 21/21 builds, v1.4.1907 (2019) through v1.9.2607 and today's `main`:

| | |
|---|---|
| preprocess succeeded | 21/21 |
| macro expanded | 21/21 |
| comments kept | **0/21** |
| control shader's `.i` contains the sentinel | **21/21** |
| `-C` / `-CC` | rejected on 21/21, in both option grammars |
| `/C` output identical to no-flag output | 21/21 |
| `/C` output identical to `/ZZZNONSENSE` output | 21/21 |

This is `always-repro'd`: for a feature that was never implemented, "the symptom
is present in every release ever shipped" is what absence looks like. There is
nothing to bisect and no regression to find.

The matrix has to be a matrix because the option grammar changed twice.
`-P` was `Separate<["-","/"],"P">` — `-P <output> <input>` — from the first
commit until `8bf2b087c` (PR #4624, 2022-08-31) made it a `Flag` and added
`-Fi`; `054e0f507` (PR #8165) later renamed `/P` to `/Po`. Releases up to
v1.7.2207 answer `Unknown argument: '-Fi'`; v1.9.2607 accepts the old form but
silently ignores the output name. No single command line spans all releases, so
the harness picks the accepted spelling per release and records which one it
used.

## Assessment

- **Status: repros** — in the sense that matters for a feature request: the
  requested capability is absent, today, on `main`.
- **Repro quality: agent-constructed** — the issue contains none.
- **Confidence: high.** Three independent lines of evidence agree: the observed
  output, the rejected flag (locally and on Compiler Explorer's own Linux
  Release builds, 1.6.2112 through trunk), and the source, which shows the
  fields being explicitly zeroed.
- **Suggested action: still-valid-keep-open.** It is a real, still-unmet
  request with a maintainer already on record that it is worth doing, and the
  triage narrows it to a specific, small change. Worth flagging as approachable
  for a first-time contributor.

## Related

#3863 ("Support -H and -P at the same time") is untriaged and is *not* triaged
here. It is noted only because it lives in the same code: the `isPreprocessing`
branch of `dxcompilerobj.cpp` handles preprocessing as an exclusive mode with a
hand-built options struct, which is also why `-H` and `-P` cannot combine. A
fix that generalises how preprocess-mode options are populated would put both
within reach; that is an observation about the code, not a triage of #3863.

## Artifacts

| file | what it is |
|---|---|
| `expected.md` | symptom written *before* any compiler was run |
| `repro.hlsl` | sentinel in comments only |
| `control-token-in-code.hlsl` | same shader, sentinel also in code |
| `cmd.txt` | 4-invocation chain; explains why the grammar-aware matrix, not generic bisect, is authoritative |
| `match.json` | 5-clause predicate: exit status + line markers + macro expansion + control + absence |
| `match-flag-rejected.json` | predicate for the flag-spelling variants |
| `out-main-debug.txt` | primary capture |
| `variant-*.txt` | negative control and the five flag-spelling probes |
| `manual-case-release-history.py` / `.txt` | the 21-build matrix and the script that made it |
| `manual-case-spelling-retry-hazard.py` / `.txt` | proof that the pre-batch-012 retry could destroy the repro |
| `manual-case-godbolt-verify.txt` | full text of the three Compiler Explorer panes |
| `godbolt-note.txt` | the banner published with the link |
