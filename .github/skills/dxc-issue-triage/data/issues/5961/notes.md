# #5961 -- Warnings about float to int conversions are wrong

## Summary

Confirmed: still reproduces on `main` (main-debug, commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465)`). The exact warning text quoted in the issue
body is reproduced verbatim, and always reproduced across every probeable stable release
(v1.4.1907 .. v1.9.2607).

## Repro

The issue links a Compiler Explorer shortlink (`https://godbolt.org/z/9PfEPYa3M`) rather than
inline source. The exact shader was recovered verbatim via
`GET https://godbolt.org/api/shortlinkinfo/9PfEPYa3M` (see `repro.hlsl`; a public repro derived
from a public issue, consistent with the skill's Compiler Explorer policy). Repro quality:
**complete**.

The reporter's CE session used `-T cs_6_6`. `cmd.txt` instead targets `-T cs_6_0`
(`cmd-as-filed.txt` keeps the original `-T cs_6_6` for reference): a labelled control
(`variant-cs60-*.txt`, `--expect match`) confirmed the identical warning text at `cs_6_0`, and
using the older profile widened the bisectable range from `v1.6.2104..v1.9.2607` (18 releases,
`cs_6_6` requires SM6.6) down to the full `v1.4.1907..v1.9.2607` (20 releases, no invalid
probes) -- the diagnostic is a language-level Sema check unrelated to shader model, so nothing
about the finding changes, and the wider range is strictly more informative.

## What the ground-truth run shows

`out-main-debug.txt` reproduces the issue's quoted stderr byte-for-byte:

```
repro.hlsl:13:19: warning: implicit conversion from 'literal float' to 'int' changes value from 2147483648 to 2147483647 [-Wliteral-conversion]
    store(to_int(-2147483648.0)); // MaxNegative int: -2147483648
```

DXC's own DXIL output for the same compile constant-folds each `to_int`/`to_uint` call at
compile time (see the `rawBufferStore.i32` operands in `out-main-debug.txt`), and those folded
values match the source-comment on each line, not the warning:

| line | expression | warning says "to" | DXIL actually folds to | comment says |
| --- | --- | --- | --- | --- |
| 13 | `to_int(-2147483648.0)` | `2147483647` | `-2147483648` | `-2147483648` |
| 14 | `to_int(-1.79...e308)` | `2147483647` | `-2147483648` | `-2147483648` |
| 15 | `to_int(1.79...e308)` | `2147483647` | `2147483647` | `2147483647` |
| 16 | `to_uint(-1.79...e308)` | `4294967295` | `0` | `0` |
| 17 | `to_uint(1.79...e308)` | `4294967295` | `4294967295` | `4294967295` |

Every line whose source literal carries an explicit unary minus (13, 14, 16) has a wrong "to"
value; the two lines without one (15, 17) are correct. That is exactly the pattern the issue
describes, and it is the reporter's own diagnosis, corroborated here independently against the
compiler's own codegen output rather than against the source comments alone.

## Root cause (source-level corroboration)

`tools/clang/lib/Sema/SemaChecking.cpp`, `AnalyzeImplicitConversions` (around line 7174):

```cpp
Expr *InnerE = E->IgnoreParenImpCasts();
// We also want to warn on, e.g., "int i = -1.234"
if (UnaryOperator *UOp = dyn_cast<UnaryOperator>(InnerE))
  if (UOp->getOpcode() == UO_Minus || UOp->getOpcode() == UO_Plus)
    InnerE = UOp->getSubExpr()->IgnoreParenImpCasts();

if (FloatingLiteral *FL = dyn_cast<FloatingLiteral>(InnerE)) {
  DiagnoseFloatingLiteralImpCast(S, FL, T, CC);
```

When the literal is written with an explicit unary minus, this code unwraps the `UnaryOperator`
and passes the **positive** inner `FloatingLiteral` to `DiagnoseFloatingLiteralImpCast`
(line 6816), discarding the sign entirely before that function converts the value and formats
both the "from" and "to" numbers for the warning (lines 6819-6846,
`llvm::APFloat::convertToInteger` + `APSInt::toString`). The actual codegen path evaluates the
whole (negated) constant expression separately and folds it correctly, which is why the DXIL
output and the warning disagree only on the negated-literal lines.

`git blame` on this block resolves to the repository's earliest visible commit for this file
(a squashed/boundary commit), i.e. the code has been present for DXC's entire trackable history
-- consistent with `bisect`'s "always-repro'd" result and with the issue's own claim that this
is inherited, pre-3.9 Clang behavior (`is this something you're going to take a look at` /
"we could go with the 3.9 changes instead" in the issue body).

## History

`bisect --linear` (`-T cs_6_0`, no invalid probes):

```
v1.4.1907 .. v1.9.2607   repro (all 20 stable releases)
```

`always-repro'd across v1.4.1907..v1.9.2607` (5 probeable prereleases excluded from the search
by policy, per the skill's release-enumeration rules). v1.4.1907 (2019-07) predates the
2023-11-02 report by more than 4 years, so this has never worked, for as long as it is possible
to check.

## Control

`control-inrange.hlsl` (`to_int(100.0)`, an exactly-representable, in-range double->int literal
conversion) emits **no** `-Wliteral-conversion` warning at all (`variant-inrange-main-debug.txt`,
`--expect no-match`, satisfied) -- confirming `match.json`'s anchor string cannot appear for
unrelated reasons; it is only ever produced by this exact out-of-range warning text.

## Supplementary: does HLSL 202x already fix this? (hypothesis, refuted by the tool, confirmed
   by inspection)

A 2024-05-03 maintainer comment on the issue speculates this "may be resolved with HLSL 202x"
via the conforming-literals proposal. Tested as a labelled hypothesis
(`variant-hv202x-main-debug.txt`, `run --hypothesis --expect match`): the tool's
`match.json` (calibrated for the default HLSL version's literal wording) scored `no-repro`
against this variant, i.e. the string-based predicate was **refuted**. That is a predicate
artifact, not evidence of a fix: under `-HV 202x` the untyped double literals are instead typed
as 32-bit `float` (a real, unrelated behavior change from conforming literals), so
`-2147483648.0` overflows `float` range to `+Inf` before the int conversion ever runs, changing
the printed numbers and additionally causing the whole compile to fail DXIL validation
("Assignment of undefined values to UAV"). But the same defect is still visible in the
resulting warning text: line 13 becomes
`implicit conversion from 'float' to 'int' changes value from 2.1474836E+9 to 2147483647`,
i.e. the source value is still printed positive (`2.1474836E+9`, not negative) despite the
literal being `-2147483648.0`. The sign-dropping bug in `AnalyzeImplicitConversions` is
version-mode-agnostic (it runs before any language-version-specific literal-typing decision),
so `-HV 202x` does not fix this defect. Do not read the tool's automatic `no-repro`
classification for this variant as a fix -- it reflects wording drift from a different,
unrelated 202x behavior change, not the absence of the reported bug. This is worth noting as a
`text_stale`-adjacent finding for the *thread*, not the issue body: the 2024-05-03 comment's
speculation is measurably not correct at this ground truth, though it is phrased as a guess
("may be") rather than an assertion, so `--text-stale` was not applied.

## Compiler Explorer

`https://godbolt.org/z/95MndY74x` -- `dxc_1_6_2112` (CE's oldest, 2021) and `dxc_trunk` both
produce byte-identical wrong warnings (`manual-case-godbolt-verify.txt`), confirming the bug is
present in every DXC build CE can show, not just the local build. Shortlink read back and
verified to match what was sent (`godbolt-note.txt` banner + panes).

## Labels

Current: `bug`, `tech-debt`, `diagnostic`. All three remain accurate; no changes proposed. The
Clang-version comparison the issue itself asks for ("track down the LLVM 3.8/3.9 change") has
effectively already been done by the reporter in the issue body, so `check-in-clang` is not
proposed (that comparison isn't outstanding work).

## Verdict

`repros`, `always-repro'd` (v1.4.1907..v1.9.2607, all probeable stable releases, plus main),
`still-valid-keep-open`, confidence high (verbatim text match to the issue's own quoted output,
corroborated against DXC's own codegen and against the emitting source, with a positive
control).
