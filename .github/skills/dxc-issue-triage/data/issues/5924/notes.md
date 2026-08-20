# Notes -- #5924 "Cannot do swizzle operations with floating type when it's a typename"

## Ground truth
`main-debug` at upstream commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(dxc 1.9.0.5465, self-reports build `7665270b9` -- verified by tree comparison:
`git diff --name-only 89e2f98e2 HEAD` touches nothing outside
`.github/skills/dxc-issue-triage/`, while the same diff against an older
commit (`758572136`) correctly shows out-of-tree files, so the two commits
share an identical compiler source tree).

## Repro
The reporter's exact source and command (`-T ps_6_0 -E PSMain`, unchanged) --
see `repro.hlsl` / `cmd.txt`. `StyleClipper<float_t>::func` is a template
static method whose parameter `t` is declared with the template type
parameter `float_t` itself; the body does `return t.xx;`. Instantiated as
`StyleClipper<float>::func`, `t`'s real type is plain `float`.

## Result on ground truth: reproduces, unchanged from the report

```
repro.hlsl:13:17: error: member reference base type 'float' is not a structure or union
        return t.xx;
               ~^~~
repro.hlsl:19:44: note: in instantiation of member function 'StyleClipper<float>::func' requested here
        return input.color + StyleClipper<float>::func(input.color.x).x;
                                                  ^
```
(`out-main-debug.txt`; exit 2147500037 = 0x80004005/E_FAIL, an ordinary
diagnosed error, not an internal failure -- this is a diagnostic-quality
issue, so `match.json` anchors the literal diagnostic text per SKILL.md's
guidance for that case.)

## Control: the issue's own claimed workaround, verified
`control-non-template.hlsl` is byte-for-byte the same shape with the one
change the reporter describes -- `func`'s parameter is declared as literal
`float` instead of the template parameter `float_t` (struct de-templated to
match). It compiles clean on the same ground truth
(`variant-control-non-template-main-debug.txt`, exit 0, `--expect no-match`
satisfied). This is exactly the reporter's "Actual Behavior" comparison,
independently reconstructed and confirmed rather than taken on faith.

Plain (non-template, top-level) scalar swizzle also compiles fine on the
same build (`control-scalar-swizzle.hlsl`, run with `--expect no-match`,
`variant-control-scalar-swizzle-main-debug.txt`, exit 0):
`float2 PSMain(float t : A) : SV_TARGET0 { return t.xx; }` emits clean DXIL.
So the defect is specific to a swizzle whose base expression's *static* type
is a template type parameter that later resolves to a scalar -- not to
scalar swizzles in general.

## Source correlation (partial, not fully traced)
The diagnostic is `err_typecheck_member_reference_struct_union`, emitted
generically in `SemaExprMember.cpp` once HLSL's own record/vector/matrix
member-expr dispatcher declines to handle the base type. That dispatcher,
`hlsl::LookupRecordMemberExprForHLSL` (`tools/clang/lib/Sema/SemaHLSL.cpp`,
~line 13331), switches on `GetTypeObjectKind(BaseExpr.getType())` and only
has cases for `AR_TOBJ_MATRIX`, `AR_TOBJ_VECTOR` and `AR_TOBJ_ARRAY`; there
is no case for `AR_TOBJ_BASIC`/`AR_TOBJ_SCALAR` (a plain `float`), so for any
call that reaches this function with a scalar base it falls through to
`default: return false` and the ordinary C++ path fails with the observed
diagnostic. This *is* reached for the template-instantiation case (a
`CXXDependentScopeMemberExpr` re-resolving `t.xx` once `float_t` is
substituted with `float`), which is consistent with what's observed.

What I did **not** fully trace is why the same dispatcher does not also
reject the plain top-level scalar case (`scratch-scalar-swizzle.hlsl`) --
some earlier stage must special-case a non-dependent scalar swizzle before
reaching this switch (or represent it differently at the type level), and I
could not pin down that stage without an AST dump (`dxc` does not accept
`-Xclang`, so the usual `-ast-dump` route is unavailable). Treat "the two
paths diverge here" as corroborated, and the precise mechanism for the
working case as unconfirmed rather than asserted.

## History
`bisect --linear`: v1.4.1907 through v1.7.2212.1 are `invalid-probe` --
`'template' is a reserved keyword in HLSL` / `use of undeclared identifier
'StyleClipper'` (`out-v1.7.2212.1.txt` etc.) -- because DXC templates first
shipped in **v1.7.2308**. From v1.7.2308 through v1.9.2607 (11 stable
releases) and on `main-debug`, every probe reproduces identically. So this
is `always-repro'd`, for as long as it has been possible to check (templates
did not exist when the issue predates them; the repro simply could not have
run before v1.7.2308, which post-dates the 2023-10-25 filing by nothing --
templates were already available when this was reported).

## Clang comparison (the `check-in-clang` label's own ask)
`godbolt --compilers "dxc_1_6_2112,dxc_trunk,hlsl_clang_trunk"`:
https://godbolt.org/z/h5q7acrv9 (shortlink read back and confirmed to hold
the intended source and all three panes' arguments).

- `dxc_1_6_2112` (exit 5): rejects `template` outright -- CE's oldest DXC
  predates template support, consistent with the release history above; not
  evidence about this bug.
- `dxc_trunk` (exit 5): same diagnostic as `main-debug`.
- `hlsl_clang_trunk` (exit 0): compiles cleanly to DXIL, computing
  `color.x + color.x` for `t.xx` (`%9`/`%10`... `fadd ... %5, %5` /
  `fadd ... %5, %6` in `manual-case-godbolt-verify.txt`). This corroborates
  @damyanp's 2024-10-24 comment ("this _looks_ like it works in clang") with
  a controlled, re-derivable measurement: the classic Sema/template frontend
  has this defect, the newer Clang-based HLSL frontend does not.

## Labels
`check-in-clang`'s own description is "See if this repros in clang as
well" -- a to-do. That comparison has now been run and answered (does not
reproduce in Clang), so per SKILL.md the label should come off rather than
stay as an open ask. Proposing `type-system` in its place: the defect is an
inconsistency in how HLSL's swizzle/member-access machinery classifies a
scalar type depending on whether it arrived via direct declaration or via
template substitution, which is exactly what that label describes.

## Suggested action
`still-valid-keep-open`. This is a real, still-reproducing compiler bug in
the classic frontend, confirmed on `main`, with a precise repro, a verified
control isolating the templated case specifically, a superseded/successor
comparison (Clang does not have it), and a release-history boundary bounded
only by when templates became available -- not a case of the bug having
regressed or been fixed at any point since.
