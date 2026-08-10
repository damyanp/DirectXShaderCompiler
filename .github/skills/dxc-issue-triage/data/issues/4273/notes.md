# Triage note - #4273

**How to remove unused cbuffer?**

- URL: https://github.com/microsoft/DirectXShaderCompiler/issues/4273
- Batch: 014
- Repro quality: `prose-only` (agent-constructed from the reporter's prose; the
  issue contains no attachable shader)
- Status vs clean `main` Debug: `repros`
- History: `always-repro'd`
- Confidence: high
- Suggested action: `enhancement-not-bug`
- Godbolt: deliberately skipped - see "Instrument" below

## Summary

`-remove-unused-globals` removes unused *loose* globals (the ones that land in
the implicit `$Globals` buffer) but never removes an explicit
`cbuffer <name> { ... }` block, even when nothing in it is referenced by the
code that survives the rewrite. That is what the reporter hit, it is what
tex3d described in the thread, it is what the code does by construction, and
an in-tree lit test has asserted it since 2020. Measured on `main` and on 19 of
the 20 stable releases that can express the option; the 20th predates the
rewriter option surface entirely. This is an accepted feature request, not a
regression and not a bug against documented behaviour.

## What the reporter asked, and what the thread settled

The report (2022-02-17) is about `IDxcRewriter2::RewriteWithOptions` with
`-E vsMain -remove-unused-globals -remove-unused-functions
-extract-entry-uniforms`, two entry points in one file, and the observation
that the rewritten source still carries the cbuffer belonging to the entry that
was *not* selected.

tex3d answered (2022-03-07) with a design position, not a workaround:

> `-remove-unused-globals` only applies to constant globals outside the context
> of explicit `cbuffer <name> { ... }` declaration blocks. [...] I think this
> was intentional, to preserve the layout of explicitly declared cbuffers.
>
> However, I don't see why complete cbuffer blocks shouldn't be removed when
> none of the constants in the block are used in the remaining code. **Let's
> consider this issue a feature request to remove completely unused cbuffer
> blocks as part of this flag.**

He also asked a narrowing question - is `psMain` itself surviving? - and the
reporter confirmed (2022-03-08) that tex3d's reading was right: the unused
entry point *is* removed, the unused cbuffer is what remains. So the title
("How to remove unused cbuffer?") understates the state of the thread: the
question was answered and the issue was converted, in place, into an accepted
enhancement. Nothing after 2022-03-08 changes that; the timeline has no
cross-reference events and the last activity is a 2024-07-24 project move.
Milestone is `Dormant`, project status `Triaged`.

The reporter's stated motivation is worth recording because it is checkable:
they feed the rewritten source onward to "generate reflect infomation and
compile", and fear "overflow the limit of cbuffer slot(15 in dx11)". See
"Does the retained block cost anything?" below - it does not, on the DXC path.

## Instrument

The reported surface is the **rewriter**, which `dxc.exe` cannot reach. This is
measured, not assumed:

- `dxc -T vs_6_0 -E vsMain -remove-unused-globals repro.hlsl` ->
  `dxc failed : Unknown argument: '-remove-unused-globals'`, exit 1
  (`variant-dxc-rejects-rewriter-flag-main-debug.txt`)
- `dxc -rewrite -E vsMain repro.hlsl` -> `Unknown argument: '-rewrite'`, exit 1
  (`variant-dxc-rejects-rewrite-mode-main-debug.txt`)

...even though `dxc --help` prints a whole `Rewriter Options:` section listing
`-remove-unused-globals` and friends (`manual-case-dxc-help-surface.txt`). The
options carry `RewriteOption` in `include/dxc/Support/HLSLOptions.td` (lines
~595-614) and are only in the accepted mask for the rewriter entry points,
while `--help` prints the entire table. Worth knowing for anyone reproducing;
not itself part of this issue.

The faithful instrument is therefore **`dxr.exe`**, registered here as compiler
id `main-debug-rw`. `tools/clang/tools/dxr/dxr.cpp` forwards its argv verbatim
to `IDxcRewriter2::RewriteWithOptions` - literally the API named in the report -
and prints the returned blob.

Two consequences:

- **`triage.py bisect` cannot produce the history and refuses to try**
  (`is_dxc_binary` / `refuse_harness_bisect`). It would substitute each
  release's `dxc.exe`, which never enters the rewriter and would answer a
  different question. The history in this note comes from a purpose-built
  matrix (`measure.py`) instead.
- **Compiler Explorer cannot run this repro at all.** CE's DXC compilers are
  `dxc.exe`; there is no rewriter pane and no `dxr`. Recorded as a deliberate
  godbolt skip rather than a link to something that does not demonstrate the
  symptom.

## Ground truth

`main-debug` / `main-debug-rw`, clean Debug build of `main` at **`13730886e`**.

    dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)

Version `1.9.0.5433` matches the expected string. The embedded `ab5400907` is a
**fork-local** SHA and is not resolvable in the public repo; `13730886e` is the
public commit and is what is cited. Captured output is left exactly as the
binary printed it. Provenance was checked by tree, not by version string:
`git diff --name-only 13730886e HEAD` restricted to everything outside the
triage skill directory is empty, and the same query against an older SHA does
list files, so it can detect a difference.

## Repro and predicate

`repro.hlsl` is agent-constructed from the reporter's own worked example
("cbA, cbB, vsMain, psMain wrote in the same file. vsMain used cbA. psMain used
cbB."), plus two loose globals - one used, one not - that act as an in-band
witness that the flag did something.

`cmd.txt` is the reporter's option list verbatim:

    -E vsMain -remove-unused-globals -remove-unused-functions -extract-entry-uniforms repro.hlsl

`match.json` is an anchored `all_of` with four clauses:

1. `cbuffer\s+cbB\s*\{` **present** - the symptom itself.
2. `float4\s+vsMain\s*\(` **present** - anti-vacuity; an empty or failed
   rewrite cannot score `repro`.
3. `psMain` **absent** - the removal pass actually ran.
4. `gLooseUnused` **absent** - `-remove-unused-globals` was honoured *by this
   build*. This is the clause that makes the release table meaningful: a
   release that ignored the flag scores `no-repro`, not `repro`.

## Primary result - `main` @ `13730886e`

`out-main-debug-rw.txt`, exit 0, verdict `repro`. Output in full:

    cbuffer cbA {
      const float4 gA;
    }
    ;
    cbuffer cbB {
      const float4 gB;
    }
    ;
    const float4 gLooseUsed;
    float4 vsMain(float4 pos : POSITION) : SV_Position {
      return pos * gA + gLooseUsed;
    }

`psMain` gone, `gLooseUnused` gone, `cbB` - referenced only by the removed
`psMain` - retained. Exactly the reported behaviour.

## Controls

All seven were run by the tool with a declared expectation, so each is
re-checked whenever the evidence is rescored.

| Capture | What it varies | Expected | Got |
| --- | --- | --- | --- |
| `variant-loose-only-main-debug-rw.txt` | no explicit `cbuffer` in the source | no-match | no-repro |
| `variant-partial-cb-main-debug-rw.txt` | unused member *inside* a used block | match | repro |
| `variant-no-remove-globals-flag-main-debug-rw.txt` | drop `-remove-unused-globals` | no-match | no-repro |
| `variant-slash-remove-globals-main-debug-rw.txt` | `/remove-unused-globals` spelling | match | repro |
| `variant-nonsense-slash-flag-main-debug-rw.txt` | add `/ZZZNONSENSE` | no-match | no-repro |
| `variant-nonsense-dash-flag-main-debug-rw.txt` | add `-ZZZNONSENSE` | invalid-probe | invalid-probe |
| `variant-misspelled-flag-main-debug-rw.txt` | `-remove-unused-global` (typo) | invalid-probe | invalid-probe |

The negative control (`control-loose-only.hlsl`) is the important one: it uses
the same options on a source with no explicit `cbuffer`, and scores `no-repro`
on **every** release in the table below, so the `repro` column is discriminating
rather than always-true.

`control-partial-cb.hlsl` sharpens the finding: an unused member inside a block
that *is* otherwise used (`gAUnusedInBlock`) also survives. So the carve-out is
"explicit `cbuffer` contents are never candidates", not merely "whole blocks
are kept".

## The flag really is parsed and honoured

`flagcheck.py` -> `manual-case-flag-parsing.txt`, 6/6 checks PASS. All on
`repro.hlsl`, ground truth:

| case | exit | `gLooseUnused` | `cbuffer cbB` | sha256 (first 16) |
| --- | --- | --- | --- | --- |
| `-remove-unused-globals` | 0 | removed | present | `986ab3c0fd5b4b33` |
| `/remove-unused-globals` | 0 | removed | present | `986ab3c0fd5b4b33` |
| flag absent | 0 | KEPT | present | `a43262a4a56ae481` |
| `/ZZZNONSENSE` added | 0 | KEPT | present | `a43262a4a56ae481` |
| `-ZZZNONSENSE` added | 1 | n/a | n/a | `81795e9205ea9925` |
| `-remove-unused-global` (typo) | 1 | n/a | n/a | `d76bf27772c3fbe0` |

Readings:

- The output with the flag differs from the output without it, so the flag is
  genuinely reaching the pass - a clean exit alone would have proved nothing.
- `/ZZZNONSENSE` exits 0 and is **byte-identical to the flag-absent run**: it is
  silently ignored. The `/`-form silent-ignore hazard is real in this driver too.
- `-ZZZNONSENSE` *is* diagnosed (`Unknown argument`), so the hazard is specific
  to the `/` prefix, not to unknown options generally.
- A one-character misspelling fails loudly, which is the cheap check that the
  real flag name was not itself a typo that happened to look like it worked.

## Release history

`measure.py --history --equiv` -> `manual-case-release-history.txt`. Since no
release archive ships `dxr.exe`, the ground-truth `dxr.exe` driver is copied
next to each release's `dxcompiler.dll` in a scratch directory, so Windows loads
that release's rewriter: the driver is held fixed and the code under test is
varied. Rows are scored by `triage.classify` imported from `scripts/triage.py`,
i.e. by the same code that scores `out-*.txt`.

| release | repro | control |
| --- | --- | --- |
| v1.4.1907 | **invalid-probe** | no-repro |
| v1.5.2010 .. v1.9.2607 (19 releases) | repro | no-repro |
| main-debug (`13730886e`) | repro | no-repro |

**v1.4.1907 is an invalid probe, proven from both sides.** By source:
`git show v1.4.1907:include/dxc/Support/HLSLOptions.td` contains no
`RewriteOption`, no `hlslrewrite_Group` and no `remove-unused-globals`;
v1.5.2010 has all three. Behaviourally: that release's rewriter *runs*
(`dxr repro.hlsl` alone exits 0 and prints `// Rewrite unchanged result:`) but
any `-`-prefixed rewriter option gives
`Compilation failed - error code 0x80070057.` (E_INVALIDARG), exit 1. The
per-release `optcheck` (`-unchanged`) failing while `noopts` succeeds is what
separates "predates the option surface" from "rewrote it clean". This matters:
`triage.classify` scores that 0x80070057 line as `no-repro`, which a naive
reading would report as "fixed in the oldest release". It is not fixed there;
the repro cannot be expressed there. (`-extract-entry-uniforms` in particular
arrived 2020-03-04 in #2730.)

So: the behaviour has been constant across the entire measurable history. There
is no regression to find and nothing to bisect.

`--equiv` cross-checks the staged-DLL mechanism against
`-external <dll> -external-fn DxcCreateInstance` on all 20 releases; SHA-256
over combined stdout+stderr is identical every time, so the table is not an
artefact of how the DLL was selected. Staging is nonetheless the mechanism of
record - `dxr` forwards `-external`/`-external-fn` into the DLL's own option
parse, and those options only became `RewriteOption` in #2730, so `-external`
is a confound on exactly the old releases where the answer is most delicate.

Six prereleases are outside the stable population and were skipped; #4273's
text names no prerelease, so none opts in under `release-policy.json`.

## Why: the code says so

`tools/clang/tools/libclang/dxcrewriteunused.cpp`, in the collection loop
(~lines 707-740), sorts top-level declarations into two buckets. A `VarDecl`
goes to `unusedGlobals` (line 723) - the set that removal later consumes at
line 913. An `HLSLBufferDecl` goes to a separate `cbufferDecls` list (line 738)
and **never** to `unusedGlobals`. Later (lines 794-796):

```cpp
  // Traverse cbuffers to save types for cbuffer constant.
  for (auto *CBDecl : cbufferDecls) {
    visitor.TraverseDecl(CBDecl);
  }
```

The cbuffers are traversed only so their types survive; they are never removal
candidates. The behaviour is structural, not an oversight in a corner case,
which is consistent with tex3d calling it intentional.

**Prior art / the test a fix must update.**
`tools/clang/test/HLSLFileCheck/rewriter/remove-unused-globals.hlsl` has said so
since 2020-04-03 (commit `a408139da`, PR #2809, Tex Riddell) - about 22 months
before this issue was filed:

    // Unused cbuffers are not removed at this time
    // CHECK: cbuffer UnusedCBuffer

and, for the member case,

    // UnusedFloat is not removed if inside a cbuffer declaration with a used global
    // CHECK: float UnusedFloat;

Any implementation of this request has to change those `CHECK` lines. Flagging
it because a contributor picking this up will otherwise be surprised by a test
that fails *because* the fix works.

## Does the retained block cost anything?

The reporter's stated harm is register-slot pressure. That is checkable on the
DXC path, so it was checked (`downstream.py` ->
`manual-case-downstream-cost.txt`): take the rewriter's own output verbatim
(`rewritten.hlsl`, still containing `cbuffer cbB`) and compile it for `vs_6_0`.

    ; Resource Bindings:
    ; $Globals                          cbuffer      NA          NA     CB0            cb0     1
    ; cbA                               cbuffer      NA          NA     CB1            cb1     1

and reflection reports `ConstantBuffers: 2`, `$Globals` and `cbA`. `cbB` gets
no binding and no reflection entry - the compiler drops it.

**Scope, stated plainly:** this measures DXC/SM6 only. The reporter said "15 in
dx11", and DX11 shaders are built by FXC for SM5.x - a different compiler,
which is not tested here and about which this note is not evidence. It is also
not evidence about a block carrying an explicit `register(bN)` binding. What it
does establish is that on the DXC path the cost of the retained block is source
cleanliness, not a consumed slot. Useful context for prioritisation; it does
not weaken the request, which tex3d accepted on its own terms.

## Labels

- now: `enhancement`, `rewriter`
- proposed add: -
- proposed remove: -

`enhancement` ("Feature suggestion") is exactly right after tex3d's conversion.
`rewriter` is the component routing label; its description reads "Bugs in the
rewriter", which fits an accepted feature request awkwardly, but that is a wart
in the label's own description and not a reason to strip the only routing signal
the issue carries. Nothing else in the taxonomy earns a place: `question` would
undo the conversion, and `up-for-grabs` / `low-hanging-fruit` are maintainer
prioritisation calls, not findings - and the required lit-test change plus the
layout-preservation design question argue against "low-hanging" anyway.

## Verdict rationale

`repros` - the reported behaviour is present in `main` at `13730886e`.
`always-repro'd` - present in every release that can express the option; the one
release that cannot is an invalid probe, not a fix. `prose-only` - the repro is
reconstructed from the reporter's worked example, not attached. `high`
confidence - four independent lines agree: measured output, an anchored
predicate with a discriminating negative control, the source structure, and a
lit test that asserts the behaviour. `enhancement-not-bug` - the maintainer
answered the question and explicitly reframed the issue as a feature request,
and the issue is already labelled `enhancement`; it should stay open as such.

## Evidence

- `expected.md` - symptom pinned down before the compiler was run
- `issue.json` - fetched issue and both comments
- `repro.hlsl`, `cmd.txt`, `match.json` - the repro, its exact command, its predicate
- `control-loose-only.hlsl`, `control-partial-cb.hlsl` - control sources
- `out-main-debug-rw.txt` - primary result
- `variant-*.txt` - the seven controls plus the three `dxc`-side captures
- `flagcheck.py`, `flagcheck.json`, `manual-case-flag-parsing.txt` - flag is honoured
- `measure.py`, `measure.json`, `manual-case-release-history.txt` - 20-release matrix
- `downstream.py`, `downstream.json`, `rewritten.hlsl`, `rewritten.dxil.txt`,
  `manual-case-downstream-cost.txt` - downstream cost of the retained block
- `manual-case-dxc-help-surface.txt` - `dxc --help` advertises what `dxc` rejects
- `comment.md` - draft comment (NOT posted)
- `method-notes.md` - observations for future batches
