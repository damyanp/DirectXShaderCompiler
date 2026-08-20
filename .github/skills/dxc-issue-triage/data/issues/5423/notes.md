# #5423 -- `dxr.exe` doesn't support macro definitions via its CLI

## Ground truth

- `main-debug` (dxc.exe): `<repo>/build/Debug/bin/dxc.exe`, self-reports
  `dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`.
  Registered `git_commit` = `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (the required upstream
  commit for this batch). Provenance verified by tree, not by the self-reported SHA: `git diff
  --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df HEAD` shows **no files outside
  `.github/skills/dxc-issue-triage/`**, while a control diff against
  `89e2f98e29c289ae8ad9e00dd310104fea9fd7df~50` shows many (`docs/DXIL.rst`,
  `include/dxc/DXIL/DxilConstants.h`, ...), proving the diff mechanism actually detects
  differences and isn't a null check. No rebuild was performed or needed for this issue.
- **This issue's actual subject, `dxr.exe`, is not part of the `main-debug` build** (only
  `dxc.exe`/`dxcompiler.dll` are built under `build/Debug/bin`). Building `dxr.exe` here would
  require a cmake rebuild, which is out of scope for this triage. Instead the already-built
  Release binary registered as compiler `dxr-5290-release`
  (`<repo>/build/Release/bin/dxr.exe`, from a prior issue's setup) is used: it self-reports
  `dxcompiler.dll: 1.10(5440-677a02a1)(1.9.0.15438) - 1.9.0.15438 (main, 89e2f98e2)` -- the
  branch label is `main` (clean, not `-dirty`) and the short SHA `89e2f98e2` is exactly the
  required ground-truth commit's prefix. No rebuild was performed to obtain or use it.
- Historical `dxr.exe` binaries for all 20 stable releases (`v1.4.1907`..`v1.9.2607`) were
  already downloaded and cached under `.cache/rw4273/<tag>/dxr.exe` by a prior batch's triage
  of issue #4273 (a different rewriter issue). Reused as-is; nothing new downloaded or built.

## The issue as filed

Two claims, one per tool, both using the trivial shader in `repro.hlsl` (a struct + PS entry
point using `float4`, matching PR #5424's own added test):

1. `dxc.exe -T ps_6_0 -E PSMain -D float4=0 repro.hlsl` -- reporter says this **fails to
   compile**, which the reporter offers as proof the macro really is expanded (the token
   `float4` gets replaced by `0` everywhere, including type positions).
2. `dxr.exe -D float4=0 -E PSMain repro.hlsl` -- reporter says this rewrites the source
   **verbatim**, with **no error or warning**, which the reporter offers as proof `dxr.exe`
   silently ignores `-D`.

## dxc.exe half: reproduced exactly, and it is the reporter's own control, not the bug

`out-main-debug.txt` (cmd.txt/match.json, ground truth `main-debug`):

```
repro.hlsl:3:5: error: expected member name or ';' after declaration specifiers
    float4 position : SV_Position;
    ^
<built-in>:66:16: note: expanded from here
#define float4 0
               ^
```

This is byte-for-byte the diagnostic PR #5424's own added test
(`tools/clang/test/HLSLFileCheck/rewriter/dxr_macro.hlsl`, added by the same PR that tried to
fix this issue) FileChecks for. Also published on Compiler Explorer (`dxc_1_6_2112` and
`dxc_trunk`, both fail identically): https://godbolt.org/z/GzETMvxvs -- see
`godbolt-note.txt` for why this link only covers the control half.

**This establishes the -D-parsing/expansion machinery is fully functional** and shared between
`dxc.exe` and `dxr.exe` (`lib/DxcSupport/HLSLOptions.cpp:542-543` parses `-D` into
`opts.Defines` for both tools identically -- it is not tool-specific code). It is the
reporter's control, not a second instance of the bug.

## dxr.exe half: the actual bug, confirmed by source and by running the binary

### Source: the CLI wrapper hardcodes "no defines", unconditionally

`tools/clang/tools/dxr/dxr.cpp:141-143` (current HEAD, unchanged from the commit that
introduced it -- see below):

```cpp
IFT(pRewriter->RewriteWithOptions(pSource, wName.c_str(), argv_, argc,
                                  nullptr, 0, pIncludeHandler,
                                  &pRewriteResult));
```

`IDxcRewriter2::RewriteWithOptions` takes the full CLI (`argv_, argc`) **and a separate**
`pDefines`/`defineCount` pair. `dxr.exe` passes `nullptr, 0` for that pair, always -- the value
does not depend on the shader, the flags, or anything else. Inside
`tools/clang/tools/libclang/dxcrewriteunused.cpp`, `RewriteWithOptions` (line ~1725) does parse
`argv_` into `opts` via `ReadOptsAndValidate`, which populates `opts.Defines` from `-D`
(confirmed above), but then forwards the **separate, always-empty** `pDefines`/`defineCount`
parameter -- not `opts.Defines` -- to every rewrite entry point it calls
(`DoRewriteGlobalCB` line 1780-1782, `DoReWriteWithLineDirective` line 1794-1796,
`DoSimpleReWrite` line 1799-1800). So `-D` is parsed and then discarded: "a field is parsed but
never read," the strongest form of source evidence this skill's method calls for.

This is exactly the defect PR #5424 (`Fixes #5423`, opened the day after this issue, closed
unmerged 2026-01-22 by an inactivity sweep -- see Discussion below) fixed, by replacing each of
those three `pDefines, defineCount` argument pairs with `opts.Defines.data(),
opts.Defines.size()`. The current source at the exact ground-truth commit still has the
pre-fix code verbatim; `git diff --name-only` against the PR's own patch was not run (the PR
was never merged, so there is nothing to diff against on this branch), but the call sites were
read directly and match the PR's "before" hunks line for line.

This repo's local git history for `dxr.cpp` is shallow (only 2 commits touch the file, oldest
2025-06-03 -- this checkout is a synthetic/condensed history for the triage environment, not
real upstream history), so git blame cannot date the introduction of this exact line beyond
that window. Within that window it has never changed. Real-world dating comes from the
release-binary matrix below instead.

### Confirmed by running the ground-truth-matched binary

`variant-dxr-groundtruth-dxr-5290-release--match-dxr.txt` (compiler `dxr-5290-release`, git
commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` -- the exact required ground truth):

```
$ dxc -D float4=0 -E PSMain repro.hlsl
[exit] 0
--- stdout ---
// Rewrite unchanged result:
struct PSInput {
  float4 position : SV_Position;
  float4 color : COLOR0;
};
float4 PSMain(PSInput input) : SV_Target0 {
  return input.color * input.color;
}
--- stderr ---
(empty)
```

Exit 0, no stderr, `float4` untouched in every position -- exactly the reported symptom: `-D`
is accepted without complaint and has no effect. The same holds for the other two rewrite
entry points PR #5424 touched: `-decl-global-cb -D float4=0` (adds an empty `cbuffer GlobalCB`
but still leaves `float4` unsubstituted --
`variant-dxr-declglobalcb-dxr-5290-release--match-dxr.txt`) and `-line-directive -D float4=0`
(`variant-dxr-linedirective-dxr-5290-release--match-dxr.txt`).

`match-dxr.json` requires both a positive anchor (the rewrite reached `PSMain(PSInput input)`,
so a crashed/errored run cannot vacuously score `repro`) and the literal un-substituted token
`float4 position` -- see the predicate's own `note` for the absence-predicate traps this avoids
and for how `out-main-debug.txt` (dxc.exe) doubles as the predicate's own positive control.

### History: always reproduced, across every stable release

`manual-case-release-history.py` re-runs the identical command
(`-D float4=0 -E PSMain repro.hlsl`) through each of the 20 cached stable release `dxr.exe`
binaries (`v1.4.1907`, which predates this 2023-07-14 report, through `v1.9.2607`, the newest
cached release) via `.cache/rw4273/<tag>/dxr.exe` -- reused from a prior batch's download, no
new download or build. Every single release, including `v1.4.1907`, produces the identical
verbatim, `-D`-ignoring rewrite (`manual-case-release-history.txt`). Combined with the
ground-truth result above: **always-repro'd**, `v1.4.1907..v1.9.2607` plus the ground-truth
commit. `triage.py bisect` was not used -- per SKILL.md's harness-as-compiler guidance, it
would substitute each release's `dxc.exe`, not `dxr.exe`, and would misreport this history.

## Discussion: a fix was written and abandoned, not merged

PR #5424 (`[rewriter] send define to rewriter functions`, opened 2023-07-16, `Fixes #5423`)
implements exactly this fix (the three call-site changes quoted above) and added the FileCheck
test this triage's dxc.exe half reproduces byte-for-byte. `llvm-beanz` (COLLABORATOR) raised an
open design objection on 2023-07-17:

> There's a big downside to supporting this. If users try to use this in patterns like the one
> described in #4357, this is an unsolvable problem in Clang. Are we really sure we want to
> open this door?

(#4357: `-D`-driven `#ifdef`s changing which types the rewriter's `-remove-unused-globals`
strips, which can make a rewrite depend on defines in a way that's hard to keep consistent.)
No further discussion followed. The PR was auto-closed 2026-01-22 as inactive for two years,
with an explicit note it can be reopened. There is no indication the design question was ever
resolved either way -- this is not a case of an agreed fix lapsing (contrast #2427), but of an
open design question that was never revisited before the PR aged out.

## Verdict

- **Status: `repros`.** Both reporter claims hold today: `dxc.exe -D float4=0` still fails to
  parse (control, matches expected behaviour); `dxr.exe -D float4=0` still silently rewrites
  verbatim (the actual bug), on the exact ground-truth commit and across all 20 cached stable
  releases plus the reporter's own `v1.7.2212`.
- **Repro quality: complete.** The issue names exact commands for both tools and a public CE
  link for the `dxc.exe` half; both were run verbatim.
- **History: always-repro'd**, `v1.4.1907..v1.9.2607` (linear, all 20 releases; `dxc.exe` half
  measured via `bisect`-equivalent ground-truth run, `dxr.exe` half via the manual matrix, since
  `bisect` cannot drive a non-`dxc.exe` tool).
- **Not-compiler-verifiable caveat:** the `dxr.exe` half could not be driven through this
  skill's standard `main-debug` ground truth or through Compiler Explorer (no rewriter pane);
  it was instead verified against an already-built Release `dxr.exe` binary whose self-reported
  commit is the exact required ground truth, plus unconditional source citation. No rebuild was
  performed for this triage.
- **Suggested action: `still-valid-keep-open`**, with the open design question from PR #5424's
  review noted rather than treated as resolved -- this is a maintainer product decision
  (whether to accept the door #4357 warns about), not something this triage can settle.
- **Text staleness:** none. The issue's own title, body and version are all still accurate.
