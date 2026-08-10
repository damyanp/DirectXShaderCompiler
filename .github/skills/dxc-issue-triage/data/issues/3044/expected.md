# #3044 — "Feature request: option to preprocess without removing comments"

Written **before** running the compiler.

## What the issue says

Opened 2020-07-16 by `jeffnn` (Jeff Noyle). **The body is empty** — the title is the entire
request. One comment, 2020-09-25, from `pow2clk` (COLLABORATOR):

> This is something that clang provides with the `-CC` flag. Presumably we can add it without
> too much difficulty.

So the request is: DXC's preprocess-only mode (`/P`, `/Po`) always strips comments, and there
should be an option — clang spells it `-C` (keep comments) / `-CC` (keep comments, including
inside macro expansions) — that preserves them.

**Repro quality: `none` in the issue.** Anything I run is `agent-constructed`.

## What "this reproduces" means

This is an enhancement request, not a defect, so "reproduces" means *the capability is still
absent*. Two claims, both of which must hold:

1. **Comments are removed.** Preprocessing a source that contains comments with `dxc /P`
   produces preprocessed text in which the comment bodies do not appear, while the
   non-comment source text does appear (and macros are expanded).
2. **No driver option turns them back on.** DXC's option table has no `-C` / `-CC`
   equivalent, so those spellings either fail to parse (`-` prefix) or are accepted-and-
   ignored (`/` prefix, which DXC silently ignores for unknown flags), and in neither case do
   comments appear in the output.

## What would falsify it (i.e. "does-not-repro" / "fixed")

* `dxc /P` output containing the comment text with no extra flag; or
* any accepted flag that makes the comment text appear. "Accepted" must be *proved*, not
  inferred from exit 0: SKILL.md records that unrecognised `/`-style flags are silently
  ignored (`/ZZZNONSENSE` exits 0), so each candidate spelling has to be made to fail — point
  it at a missing input file — to show the parser saw it at all.

## Where to look in the tree (claims to check, before measuring)

* `include/dxc/Support/HLSLOptions.td` — does any option spell `C`/`CC`? (`Cc` exists and is
  something else: "Output color coded assembly listings".)
* `tools/clang/tools/dxcompiler/dxcompilerobj.cpp` — the preprocess path builds
  `clang::PreprocessorOutputOptions` by hand. If `ShowComments` / `ShowMacroComments` are
  fields that exist but are hardcoded to 0, then the capability is *present in the library and
  unreachable from the driver*, which is a much more actionable finding than "not supported":
  it turns the request into option plumbing rather than a feature.
* `tools/clang/lib/Frontend/PrintPreprocessedOutput.cpp` — does it honour those fields?
* `tools/clang/lib/Frontend/CompilerInvocation.cpp` — clang's own `-C`/`-CC` parsing, and
  whether the code path that reads it is reachable from `dxc.exe` at all.

## Predicate hazards I expect to have to handle

* The symptom is an **absence** (the comment text is gone). An absence clause is satisfied for
  free by a compile that failed and printed nothing, so the predicate needs a positive anchor
  plus an in-predicate self-test proving the instrument *can* see a token of the same shape in
  the same run.
* `dxc /P` writes its output to a **file** (`/Fi`, else `<input>.i`), not to stdout, so the
  text under test has to be brought back onto stdout by a second invocation before any
  predicate can score it.
* A probe of "is `-C` accepted?" trips the `Unknown argument` spelling re-probe in `run`.
  That machinery is correct and must not be defeated by hand-coding one spelling — so keep
  flag-acceptance out of the primary predicate and measure it in labelled variants.

## History question

For a never-implemented feature the interesting history is "has any shipped release ever had
it?", which is a population claim over the stable releases, not a transition. Expect
`never-repro'd-in-releases` to be the *wrong* wording here — the predicate polarity is
"capability still absent", so `always-repro'd` is what absence looks like.
