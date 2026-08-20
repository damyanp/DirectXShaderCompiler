# #5567 -- `-Wcomma-in-init` should maybe be more aggressive?

## Ground truth

`main-debug` registered at `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(`[HLSL] Add LinAlg descriptor I/O offset, stride and layout coverage (#8762)`).

The locally built binary self-reports commit `7665270b9` (`--version`:
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)`),
which is a later commit on this triage branch. Verified equivalence by tree, not by
SHA:

```
git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df 7665270b9
  -> 0 files outside .github/skills/dxc-issue-triage
git diff --name-only 89e2f98e29c289ae8ad9e00dd310104fea9fd7df~50 7665270b9
  -> 115 files outside .github/skills/dxc-issue-triage   (control: the check can detect a real difference)
```

So the build is a clean ground-truth build of `89e2f98e...`: every intervening
commit on the branch touches only the triage skill directory. No rebuild was
needed or performed for this issue.

## The issue

`uint2 a = (1, 2);` gets `warn_hlsl_comma_in_init`
("comma expression used where a constructor list may have been intended",
`-Wcomma-in-init`). `uint2 a = (1, 2) / 2;` -- the reporter's actual bug, a
forgotten `uint2(...)` constructor -- does not, even though it is the same typo.
The reporter asks whether the diagnostic should look inside a larger expression,
not only at the initializer expression itself.

## Source reading

`tools/clang/lib/Sema/SemaHLSL.cpp`:

```cpp
static bool IsExpressionBinaryComma(const Expr *expr) {         // line 2190
  expr = expr->IgnoreParens();
  return expr->getStmtClass() == Expr::StmtClass::BinaryOperatorClass &&
         cast<BinaryOperator>(expr)->getOpcode() == BinaryOperatorKind::BO_Comma;
}
...
Expr *firstArg = Args.front();
if (IsExpressionBinaryComma(firstArg)) {                          // line 8836
  m_sema->Diag(firstArg->getExprLoc(), diag::warn_hlsl_comma_in_init);
}
```

`IsExpressionBinaryComma` only strips parentheses before checking for a top-level
comma `BinaryOperator`. For `(1, 2) / 2`, `firstArg` is the `/` `BinaryOperator`
whose LHS is the comma expression -- the check never looks inside it, so the
warning cannot fire, exactly matching the reported gap.

`git log --all -S"IsExpressionBinaryComma"` finds only two hits: `6ee4074a4`
("first commit", 2016-12-28) and `8a8b29f96` ("[spirv] AMD work graphs
extension (#7353)"). The latter's diff for this file is `@@ -0,0 +1,17631 @@`
(the whole file as one hunk with no removed lines) -- an artifact of that
commit rewriting/re-squashing large parts of the file's history, not a second
edit of this function; there is exactly one definition of
`IsExpressionBinaryComma` in the current tree, byte-identical to the one added
in "first commit". So this check has had this exact one-level-only shape since
before this repository's public history begins, i.e. always, for as long as it
is checkable.

## Repro

```hlsl
[numthreads(1, 1, 1)]
void main()
{
  uint2 a = (1, 2) / 2;
}
```
`dxc -T cs_6_6 repro.hlsl -Od` (verbatim from the issue).

`main-debug` (`out-main-debug.txt`): exit 0, clean DXIL, **no diagnostic at
all** in stdout or stderr -- the gap still exists.

**Control** (`control-direct-comma.hlsl`, same comma pair with no division,
`--expect no-match`): exit 0, and stderr does contain
`control-direct-comma.hlsl:4:13: warning: comma expression used where a
constructor list may have been intended [-Wcomma-in-init]` (`variant-control-direct-main-debug.txt`).
This proves the diagnostic itself is still implemented and the pipeline still
reaches this check -- the repro's silence is specifically about the
division-wrapped form, not a regression that removed the warning outright.

## History

```
python scripts/triage.py bisect --issue 5567
```
`v1.4.1907` and `v1.5.2010` are `invalid-probe` (`error: invalid profile
cs_6_6` -- SM 6.6 did not exist yet; `# invalid-probe-reason:` in
`out-v1.5.2010.txt` confirms the classifier's own reasoning). `v1.6.2104` and
`v1.9.2607` both `repro`; binary search short-circuited on endpoint agreement.
Result: **always-repro'd across v1.6.2104..v1.9.2607** (2 unprobeable releases
skipped, 5 prereleases excluded from the search by policy). No linear scan was
run: nothing in the issue or its one comment suggests a fix-then-revert
history, and the source reading above shows the check's narrow one-level shape
has not changed since before v1.4.1907 (2019-07), so a hidden mid-history
window is not plausible here. cs_6_6 first shipping at v1.6.2104 (2021-04)
also means no probeable release covers the reporter's own 2023-08 report --
consistent with the source dating that this predates the whole release
matrix.

## Compiler Explorer

`https://godbolt.org/z/dPM8vnz5b` (`dxc_1_6_2112`, `dxc_trunk`,
`hlsl_clang_trunk`; full panes in `manual-case-godbolt-verify.txt`, read back
and verified by the tool).

Both DXC panes (CE's oldest, 1.6.2112, and current trunk) agree with
`main-debug`: exit 0, no diagnostic. `hlsl_clang_trunk` (the from-scratch HLSL
front end being built in upstream `llvm-project`, a different codebase from
this repository) **does** warn on the identical construct:

```
<source>:14:14: warning: left operand of comma operator has no effect [-Wunused-value]
   14 |   uint2 a = (1, 2) / 2;
      |              ^
```

This corroborates damyanp's 2024-10-09 comment ("clang current does emit a
warning in these cases") with a live measurement, nearly two years later. Note
it is a *different*, more general diagnostic (`-Wunused-value`, the generic
C-family "comma operand has no effect" warning that fires on any discarded
comma-operator LHS) rather than a semantic `-Wcomma-in-init`-style check for a
likely-typo'd constructor list -- but it does catch exactly the case DXC's
narrower, single-level check misses.

## Assessment

`repros` / `always-repro'd`. This is a diagnostic-quality enhancement request,
not a crash or miscompile: the shader always compiled correctly either way,
and the only gap is a missed opportunity to warn. `IsExpressionBinaryComma`'s
one-level structure has been unchanged since before the oldest probeable
release, and the successor Clang front end already flags the same construct
(via a different, more general warning) -- both of which support treating this
as a small, well-scoped, still-open improvement to `-Wcomma-in-init` rather
than something requiring product/design judgement.

No `text-stale` finding: the issue title and body still describe current
behaviour accurately (the maintainer's clang comment is corroborating context,
not a claim about DXC itself, and does not contradict the report).
