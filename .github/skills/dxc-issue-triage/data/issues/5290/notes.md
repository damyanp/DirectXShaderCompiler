# #5290 -- Rewriter: entrypoint function's param referenced types are removed when param is not used

## Ground truth

`main-debug` = `build/Debug/bin/dxc.exe`, registered at commit
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` (this batch's assigned ground
truth). Re-verified for this issue, independently of trusting the registry:

- `dxc --version` on the registered exe reports `1.9.0.5465 (triage,
  7665270b9)` -- a fork-local branch commit that resolves nowhere public.
  Cited commit is `89e2f98e2...`, the upstream SHA the *source* corresponds
  to, not what the binary self-reports.
- Tree check: `git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  HEAD -- . ':!.github/skills/dxc-issue-triage'` is **empty**.
- Control: `git diff --name-only
  "89e2f98e29c289ae8ad9e00dd310104fea9fd7df^" 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  -- . ':!.github/skills/dxc-issue-triage'` reports
  `tools/clang/unittests/HLSLExec/LinAlgTests.cpp` -- proves the query can
  detect a real source difference when one exists.
- `.cache/compilers/main-debug.json`'s `git_commit` field already recorded
  `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` from a prior batch step; this
  triage only re-verified it (no re-registration, no rebuild).

## The tool under test is `dxr`, not `dxc`

The issue's repro command is `dxr.exe -remove-unused-functions
-remove-unused-globals -E ps_main` (the title says "dxr.exe", not the more
common typo target "dxc.exe" -- `dxr` is the standalone rewriter driver,
`tools/clang/tools/dxr`, a thin wrapper over `IDxcRewriter2`/`RewriteUnused`).
`dxc.exe` does not expose this surface:

```
$ dxc -remove-unused-functions -remove-unused-globals -E ps_main -T ps_6_0 repro.hlsl
dxc failed : Unknown argument: '-remove-unused-functions'
```

(`variant-dxc-rejects-rewrite-flags-main-debug.txt`, run against the real
registered `main-debug` ground truth, `--expect invalid-probe`, confirmed.)
This exact tool boundary was independently established for #5255 in this
same batch.

**No rebuild was done for this issue.** `build/Debug/bin/` in this checkout
does not contain `dxr.exe` (the Debug tree here was built for the `dxc`
target only). Rebuilding `dxr` would touch the shared Debug build tree other
batch-019 workers may be measuring, which this triage explicitly must not do.

Instead, `build/Release/bin/dxr.exe` (already present on disk, untouched,
built 2026-07-20) was used read-only -- the same binary #5255 used in this
batch, already registered there as `dxr-5255-release`. It self-reports
`dxcompiler.dll: 1.10(5440-677a02a1)(1.9.0.15438) - 1.9.0.15438 (main,
89e2f98e2)`: the `89e2f98e2` prefix matches this batch's ground-truth commit
exactly. Registered here as a second, non-colliding compiler id
`dxr-5290-release` (`triage.py compiler --id dxr-5290-release ...`); the
existing `dxr-5255-release` / `main-debug-rw` rows were left untouched. This
is not a Debug-vs-Release concern the way crash issues are: the defect is an
AST-traversal/text-emission logic bug with no assert or crash involved,
observable identically regardless of `NDEBUG`.

## Two asks, decomposed and scored separately

The issue body reports one bug; a top-level comment and the reporter's own
follow-up comment describe a second, related one. Per the skill's
"decompose multi-ask issues" guidance, each gets its own repro, control and
`match*.json`.

### Ask 1 (the title): entry point's own unused parameter type is dropped

`repro.hlsl` is the issue body's shader verbatim: `ps_main(VS_OUTPUT input)`
never reads `input`.

```
$ dxr -remove-unused-functions -remove-unused-globals -E ps_main repro.hlsl
[exit] 0
float4 ps_main(VS_OUTPUT input) : SV_Target0 {
  return float4(0, 0, 0, 0);
}
```

(`out-dxr-5290-release.txt`.) **Byte-identical** to the issue's quoted output:
`struct VS_OUTPUT { ... };` is gone even though `ps_main`'s own signature
still names it.

Control (`control-param-used.hlsl`, identical shape but `return
input.color;`, `--expect no-match`, scored `no-repro` in
`variant-param-used-dxr-5290-release.txt`): when the parameter is actually
read, `VS_OUTPUT` is correctly retained. Isolates the trigger to the
parameter itself being unused, not to anything else about the shape.

### Ask 2 (second comment): a nested struct dropped via a local variable's cast

`repro2.hlsl` is the second comment's shader verbatim (adds `VS_APPEND`,
`LayerColor`, `Material`, and a local `Material mtl = (Material)0;` inside
`ps_main`, itself never read afterwards).

```
$ dxr -remove-unused-functions -remove-unused-globals -E ps_main repro2.hlsl
[exit] 0
float4 ps_main(VS_OUTPUT input) : SV_Target0 {
  Material mtl = (Material)0;
  return float4(0, 0, 0, 0);
}
```

(`variant-nested-struct-dxr-5290-release--match-nested.txt`.) `struct
Material { ... };` (and, incidentally, `struct VS_OUTPUT`/`struct VS_APPEND`
-- ask 1's defect, since this shader's parameter is also unused) are all
missing, exactly as the reporter describes ("The struct `Material` will be
removed").

Control (`control-local-used.hlsl`, identical shape but `return
mtl.colors[0].r;`, `--expect no-match`, scored `no-repro` in
`variant-local-used-dxr-5290-release--match-nested.txt`): when `mtl` is
actually read afterwards, `Material` is correctly retained.

Anti-vacuity control (`--args "... -E no_such_entry repro.hlsl"`, label
`entry-not-found`, `--expect no-match`,
`variant-entry-not-found-dxr-5290-release.txt`): a nonexistent entry point
makes `dxr` fail before emitting any rewritten source (`//entry point not
found`), and correctly scores `no-repro` -- `match.json`'s positive anchor
clause prevents a failed/empty run from vacuously satisfying the absence
clause.

## Root cause, corroborated by code reading -- one defect, not two

`tools/clang/tools/libclang/dxcrewriteunused.cpp`'s `CollectRewriteHelper`
seeds `unusedTypes` with every top-level `TagDecl`, then traverses reachable
code with `VarReferenceVisitor` (a `RecursiveASTVisitor`) starting from
`entryFnDecl`, erasing a type from `unusedTypes` only when
`VisitDeclRefExpr`'s `VarDecl` branch fires:

```cpp
} else if (VarDecl *varDecl = dyn_cast_or_null<VarDecl>(valueDecl)) {
  m_unusedGlobals.erase(varDecl);
  if (TagDecl *tagDecl = varDecl->getType()->getAsTagDecl()) {
    AddRecordType(tagDecl);   // marks the type "used"
  }
  ...
}
```

`VisitDeclRefExpr` only runs for an actual **name reference** to an
already-declared `VarDecl` -- i.e. the variable being *read* somewhere else
in the code, not for the variable's own declaration. `RecursiveASTVisitor`'s
default traversal walks `entryFnDecl`'s `ParmVarDecl`s (ask 1) and any local
`VarDecl`s in its body (ask 2) as part of walking the function, but
`VarReferenceVisitor` overrides neither `VisitParmVarDecl` nor `VisitVarDecl`
nor any `Visit*TypeLoc` hook, so neither a parameter's declaration nor a
local variable's declaration/initializer-cast is itself treated as "using"
its type. `grep`-confirmed: `entryFnDecl->parameters()`/`->param_begin()`/
`params()` is never referenced anywhere in this file's git history
(`git log --all -S "parameters()" -- tools/clang/tools/libclang/dxcrewriteunused.cpp`
returns nothing), so the entry point's own signature has never been walked
for this purpose.

This is why **both** controls above flip the verdict identically: what
distinguishes a "kept" struct from a "removed" one is not whether the
variable/parameter is itself referenced by the function signature or a
local declaration, but whether some *other* expression later reads it via a
`DeclRefExpr`. Ask 1 and ask 2 are the same root cause reached through two
different `Decl` kinds (`ParmVarDecl` vs. local `VarDecl`), not two separate
bugs -- matching the second comment's implicit framing ("I have already fix
this [ask 1], then I found this bug [ask 2]") as two symptoms of one gap
rather than two independent defects requiring two independent fixes.

Top-level comment (Snowapril, 2023-06-14) independently reaches the same
conclusion for ask 1: "solved by iterating entryFnDecl->params and remove
param type from collected 'unusedTypes' in CollectRewriteHelper." The
reporter's reply ("I have already fix this") reads as a private/local patch,
not a claim that any upstream fix landed -- no PR from either account exists
on GitHub (`gh search prs --repo microsoft/DirectXShaderCompiler "5290"`
returns nothing), and the issue remains open.

## History: release matrix (`dxr` is a harness, `bisect` refuses)

`triage.py bisect` hard-errors for this issue (`refuse_harness_bisect` /
`is_dxc_binary`): the registered ground-truth executable's filename is
`dxr.exe`, not `dxc`/`dxc.exe`, and `bisect` would otherwise substitute each
release's `dxc.exe` -- which never calls the rewriter -- and could report a
confident, wrong verdict (same shape as #4273, #5255, #3237, #2923).

Followed the #4273/#5255 pattern (`measure.py --history`, this issue's own
copy): stages the ground-truth `dxr.exe` next to each cached stable release's
own `dxcompiler.dll` under `.cache/rw5290/<tag>/`, so Windows' DLL search
order loads that release's rewriter, driven by the fixed, known-good `dxr`
binary. Six probes per release (`ask1`, `ask1-ctrl`, `ask2`, `ask2-ctrl`,
`optcheck`, `noopts`); scored with `triage.classify` and this issue's own
`match.json`/`match-nested.json` -- the same code that scores `out-*.txt`.
Full output: `manual-case-release-history.txt`; `measure.json` has the
machine-readable rows.

| release | ask1 | ask1-ctrl | ask2 | ask2-ctrl | reading |
| --- | --- | --- | --- | --- | --- |
| v1.4.1907 | no-repro | no-repro | no-repro | no-repro | **invalid-probe** -- `-unchanged` exits 1 while the no-option run exits 0: this release's rewriter runs but has none of these options yet |
| v1.5.2010 .. v1.9.2607 (all 20 stable releases) | repro | no-repro | repro | no-repro | repro |
| `dxr-5290-release` (main, 89e2f98e2) | repro | no-repro | repro | no-repro | repro |

Both controls score `no-repro` on **every** probeable release, so the
used-vs-unused distinction that isolates the root cause holds across the
whole history, not just on ground truth.

**Always reproduced, for as long as this is checkable.** `git log --all -S
"unusedTypes" -- tools/clang/tools/libclang/dxcrewriteunused.cpp` (oldest
first) dates the type-removal feature itself to `7e780aef6`
("Fix crash when remove unused globals in rewriter and support remove
types. (#2933)", 2020-05-30 -- confirmed via `git show -s --format="%h %ci
%s"`), which predates `v1.4.1907`'s successor `v1.5.2010` (2020-10-22). So
the defect has existed since the feature it is part of was introduced, and
every probeable stable release inherits it. `v1.4.1907` (2019-07) itself
predates the rewriter's `-remove-unused-*` option surface entirely and is
`invalid-probe`, not evidence either way -- confirmed both by `optcheck`
exiting 1 there while `noopts` exits 0, and independently by `git log -S
"remove-unused-globals" -- include/dxc/Support/HLSLOptions.td` showing the
options postdate that release.

## Cross-reference timeline

`gh api repos/microsoft/DirectXShaderCompiler/issues/5290/timeline` returns
**zero** `cross-referenced` events -- no PR or other issue links here, and
this triage created none (checked again after all `run`/`godbolt` calls
above).

## Text staleness

None. The title and body still describe exactly what the compiler does. The
reporter's "I have already fix this" is, on its own words, about their own
local patch for ask 1 specifically (made in response to Snowapril's
suggestion), not a claim that upstream is fixed -- and it does not address
ask 2 at all, which the same comment goes on to report as newly found. No
comment claims the issue as a whole is resolved.

## Verdict

- status: `repros` (both asks)
- repro-quality: `complete` (both shaders are runnable verbatim from the
  issue text; ask 2's is quoted in full in a comment, including the
  intermediate `VS_APPEND`/`LayerColor` types)
- history: `always-repro'd` across every checkable release (`v1.5.2010` ..
  `v1.9.2607`, 20 stable releases) and `main` (89e2f98e2); `v1.4.1907` is an
  invalid probe (predates the rewriter's `-remove-unused-*` options)
- confidence: high
- suggested action: `still-valid-keep-open` -- no PR references this issue
  and no fix has landed; the root cause is understood and corroborated by
  code reading, an empirical used/unused control pair, and a clean 20-release
  history, but nothing here supersedes maintainer review of an actual patch.
