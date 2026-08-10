# 3863 — "Support -H and -P at the same time"

Written **before** running the compiler.

## What the issue says

Opened 2021-07-07 by `Ceffa93` (Filippo Ceffa). Label: `enhancement`. Body, in full:

> The -P flag runs the dxc preprocessor.
> The -H flag outputs a list of all headers included. (there is also a similar-Vi option)
>
> The -H flag is only available when running a regular dxc build.
> It is not available when running only the preprocessor.
>
> This strikes me as odd, because as far as I can tell, the information that -H produces come
> from the preprocessor, not from the build. The preprocessor must know about all the includes
> to do its job.
>
> I am personally in a situation where I only use dxc as a preprocessor, and I need to obtain
> the list of included headers. I have no way of doing so without running a full build, or
> manually parsing the preprocessed output.

Two comments:

* 2021-11-18, `pow2clk` (COLLABORATOR): *"Not to dismiss this issue. I'm currently unaware of
  any reason for the restriction beyond lack of imagination, but it's possible that this
  pending PR will give you what you need as it outputs the dependencies of a given shader
  file #4017"*
* 2023-06-30, `llvm-beanz` (COLLABORATOR): *"Related: #5117, #4723"*

**Repro quality in the issue: `prose-only`.** The behaviour is described precisely and the two
flags are named, but there is no shader, no header, no command line and no captured output.
Everything below is agent-constructed from that description.

## What "this reproduces" means

This is an enhancement request, so "reproduces" means *the requested capability is still
absent*. Three claims, and all three must hold for the symptom to be present:

1. **`-H` works on a normal compile.** `dxc -T ps_6_0 -E main -H <src>` prints an
   `Opening file [...], stack top [...]` line for each header it opens. Without this the
   instrument is dead and any absence below is free.
2. **`-P` really preprocesses and really resolves the include.** The preprocessed output
   contains the *body* of the included header, so the preprocessor demonstrably opened it.
3. **`-H` produces no include list in `-P` mode.** No `Opening file [` line naming the
   header that the `-P` arm included appears anywhere in that run's output.

## What would falsify it (i.e. "does-not-repro" / "fixed")

* An `Opening file [` line naming the `-P` arm's header, on stdout or stderr; or
* any other include listing emitted by the `-P` invocation itself.

Note what is **not** falsification: `-P -H` exiting 0. Exit 0 here is the *symptom* — a
silently-ignored option — not evidence of success.

## Proving `-H` was actually parsed, not silently swallowed

SKILL.md records that `/`-prefixed unknown flags are silently ignored by dxc, so exit 0 proves
nothing. `-H` is spelled `Flag<["-"], "H">` — dash only — and dxc *does* diagnose unknown
`-` arguments, so a nonsense dash flag in the same position is the control:
`-ZZZNONSENSE3863` must be rejected where `-H` is not. Independently, #3044 settled this class
of question with byte comparison, and that is the stronger instrument here too: **SHA-256 of
the preprocessed output with `-H` and without `-H` must be compared.** If `-H` had any effect
on the artifact the hashes differ; if they are identical, `-H` changed nothing about what `-P`
produced, which is precisely the reporter's complaint.

`-Vi` is `Alias<H>` in `HLSLOptions.td`, so the issue's "similar -Vi option" must be probed
too — and it accepts the `/` prefix, so `/Vi` is *not* usable as evidence of anything.

## Where to look in the tree (claims to check, before measuring)

* `include/dxc/Support/HLSLOptions.td` — `def H : Flag<["-"], "H">` and
  `def _vi : Flag<["-","/"], "Vi">, Alias<H>`; `def P`, `def Po`, `def Fi`.
* `lib/DxcSupport/HLSLOptions.cpp` — `opts.DisplayIncludeProcess = Args.hasFlag(OPT_H, ...)`.
  Is there a rule that rejects or drops `-H` when `Preprocess` is non-empty? There is a
  "compiler options ignored with Preprocess" warning near the `Preprocess` checks — **is
  `DisplayIncludeProcess` in its list?** If it is, the combination is deliberately rejected.
  If it is not, the combination is unimplemented rather than refused, which is a materially
  different finding and a much smaller fix.
* `tools/clang/tools/dxcompiler/dxcompilerobj.cpp` — `EnableDisplayIncludeProcess()` is called
  before the `isPreprocessing` branch, so does the trace get produced in preprocess mode?
  Where does the collected stdout text go — is it stored on the result?
* `tools/clang/tools/dxclib/dxc.cpp` — `DxcContext::Preprocess()` versus
  `DxcContext::Compile()`. Which of them reads the result output that carries the trace?
* `tools/clang/test/DXC/include-main.hlsl` and `show-includes.hlsl` — the existing `-H`/`-Vi`
  tests, i.e. the exact text a fix would have to keep producing.

If the trace turns out to be *produced and then dropped by the driver*, that is the finding,
and it should be verified by a measurement and not only by reading — see below.

## Planned probes

| probe | what it decides |
| --- | --- |
| `cmd.txt` line 1: `-T ps_6_0 -E main -H control-compile.hlsl` | in-predicate self-test: `-H` is alive in this build and in this run |
| `cmd.txt` line 2: `-P repro.hlsl -Fi preprocessed.i -H` | the repro |
| `cmd.txt` line 3: `-T ps_6_0 -E main -Zi preprocessed.i` | brings the preprocessed text onto stdout (see hazards) so clause 2 above can be checked |
| variant `-ZZZNONSENSE3863` in `-H`'s position | control: an unparsed dash flag *is* diagnosed |
| variant `-Vi` in `-H`'s position | the alias the issue also names |
| variant: `-P` with no `-H` | byte comparison of the produced `.i` |
| variant: `-M` (with and without `-H`) | `#4017` shipped `-M`; does it answer the reporter's actual need, and does `-H` print on that path? |
| API probe via `dxcompiler.dll` | if the source says the trace is captured but not printed, measure it: `IDxcResult::HasOutput(DXC_OUT_REMARKS)` after a `-P -H` compile |

## Predicate hazards I expect to have to handle

* The symptom is an **absence**, so it is satisfied for free by a run that failed, and
  falsified for free by a run that never included anything. Hence clauses 1 and 2 above are
  *required* clauses of `match.json`, not prose.
* `dxc -P` writes to a **file**, never to stdout (#3044 measured this), so the preprocessed
  text has to be re-emitted by a second invocation compiling the `.i` with `-Zi`, which
  embeds it in `!dx.source.contents`.
* Both arms are in one capture, so the two headers must have **different file names** or the
  self-test and the absence clause cannot be told apart.
* The absence regex must be anchored on the literal `Opening file [` prefix. The header's own
  name appears in `#line` markers inside the preprocessed text, and an unanchored search for
  the file name would match those and manufacture a "fixed" result.

## History question

`-P`'s grammar changed at `8bf2b087c` (PR 4624, 2022-08-31): before it, `P` is
`Separate<["-","/"],"P">` and `-P <name>` names the **output** file, with no `-Fi`. One command
line therefore cannot be run across all releases, and the `/Fi` spelling retry on the old
grammar is the mutation hazard #3044 recorded. Expect to need an explicit grammar-aware
matrix rather than generic `bisect`, and expect it to have to visit **every** stable release
(a linear scan), because the issue was filed in 2021 — inside the release range — and matching
clean endpoints would not exclude a mid-history window.

For a never-implemented capability the correct history value is `always-repro'd`;
`never-repro'd-in-releases` would read as "we could not reproduce it", which is the opposite
claim.

## Relationship to #3044 — to be decided from evidence, not assumed

#3044 asks for comment retention during `-P`. Both live in the same `isPreprocessing` branch.
Before calling them duplicates I have to answer: is the *missing mechanism* the same one? If
#3044's gap is a hardcoded `PreprocessorOutputOptions` field and #3863's gap is somewhere else
entirely (option validation, or the driver's output writing), they are neighbours and not
duplicates. Record the answer either way.
