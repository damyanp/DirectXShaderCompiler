# Notes -- #5194 "Impossible to add template on operator() overload"

## Ground truth

`main-debug` is registered at git_commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`
(public upstream), self-reporting
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)` --
the local build's own commit (`7665270b9`) differs from the cited upstream
SHA because it was built on a local working branch (see SKILL.md's "cite a
publicly resolvable commit" note). Verified equivalence with a controlled
tree diff instead of trusting the self-reported SHA:

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  | grep -v outside .github/skills/dxc-issue-triage/   -> 0 files
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df~200
  | grep -v outside .github/skills/dxc-issue-triage/   -> 609 files
```

Zero source files outside the skill tree differ from the cited upstream
commit, and the control against an older commit (`~200`) shows 609 files
differing outside the skill tree, so the diff check has power to detect a
real difference and found none. The Debug build is therefore equivalent to
upstream `89e2f98e2` for triage purposes.

## Repro

The issue body's shader compiles unmodified. The reporter's own Compiler
Explorer link (`https://godbolt.org/z/vx15Ybd1f`, read back through
`GET /api/shortlinkinfo/vx15Ybd1f`) pins the exact configuration used:
compiler `dxc_1_7_2207`, options `-spirv -HV 2021 -T cs_6_2`. `cmd.txt`
reproduces that exactly, adding only `-E main` (dxc's local driver needs an
explicit entry point; CE's compiler preset supplies it implicitly).

Repro quality: **complete**.

## Predicate (`match.json`)

`any_of` over three literal error-text anchors, one per call form in the
issue:

1. `t(5)` (implicit template-argument deduction on the call operator) --
   `no matching function for call to object of type 'Test'`
2. `t<uint>(5)` (explicit-template-id call syntax) -- `unexpected type name
   'uint': expected expression`
3. `t.operator()<uint>(5)` (explicit member-call syntax) -- `no matching
   member function for call to 'operator()'`

This is a diagnostic-quality issue in the SKILL.md sense (the reported
symptom *is* a set of diagnostics), so the predicate matches on message
text with an `any_of`: the bug is that all three legal-looking forms are
rejected, and it counts as still reproducing as long as at least one still
errors.

Not an `internal_failure` predicate: dxc runs to completion and returns a
diagnosed Sema error, `0x80004005` (E_FAIL), verified in every capture's
`# exit:` line -- this is not a crash issue.

**Control**: `control-non-template.hlsl` replaces the templated
`operator()` with an ordinary one and calls it the same way (`t(5)`).
Expected `no-match`; measured `no-match` (`variant-control-main-debug.txt`,
exit 0). This shows the predicate is keyed to *template* overload
resolution on `operator()` specifically, not to `operator()` calls or
`Test`-shaped structs in general.

**Per-clause isolation controls** (identity/`--expect match`, run against
main-debug so `audit` has a tool-made capture for every `.hlsl` beside the
issue): `variant-clang-call1.hlsl`, `variant-clang-call2.hlsl` and
`variant-clang-call3.hlsl` each contain exactly one of the three call
forms. All three independently reproduce against classic DXC
(`variant-call1-only-main-debug.txt`, `variant-call2-only-main-debug.txt`,
`variant-call3-only-main-debug.txt`, all exit `0x80004005`, all matched),
confirming each of the three `any_of` clauses is individually load-bearing
and not merely satisfied by interaction between the three lines.

## History (`bisect`)

```
skipped 1 release (no usable dxc asset): v1.2.0-alpha
skipped 5 prereleases from search by policy
v1.4.1907   invalid-probe -- "Unknown HLSL version: 2021" (-HV 2021 postdates this release)
v1.5.2010   invalid-probe -- same marker
v1.6.2104   invalid-probe -- same marker
v1.6.2106   invalid-probe -- same marker
v1.6.2112   repro
v1.9.2607   repro
result: always-repro'd across v1.6.2112..v1.9.2607
```

`-HV 2021` (HLSL 2021 language mode) did not exist before v1.6.2112
(2021-12-08), so the four oldest stable releases reject the command before
ever reaching the code under test (`out-v1.4.1907.txt`,
`out-v1.5.2010.txt`, `out-v1.6.2104.txt`, `out-v1.6.2106.txt`, each
tagged `invalid-probe-reason: ... "Unknown HLSL version: 2021"`).
`bisect` checked both probeable endpoints (v1.6.2112, v1.9.2607), both
reproduce, and it short-circuited: **always-repro'd**, i.e. this was never
implemented, not a regression. v1.6.2112 (2021-12-08) predates the report
(2023-05-09) by 17 months, so the probeable history covers the issue's
whole life; nothing older can be asked the question because the reporter's
own `-HV 2021` flag postdates it.

`main-debug` reproduces (`out-main-debug.txt`, exit `0x80004005`,
all three diagnostics present, matching `out-v1.6.2112.txt` /
`out-v1.9.2607.txt` verbatim).

## Compiler Explorer

`https://godbolt.org/z/9ajqv56xK` (read back and verified via
`shortlinkinfo`) -- `dxc_1_6_2112`, `dxc_trunk` and `hlsl_clang_trunk`, all
on the unmodified `repro.hlsl` plus the `godbolt-note.txt` banner. CE's
`dxc_1_6_2112` and `dxc_trunk` panes (Linux Release builds) both exit 5
(E_FAIL truncated, per SKILL.md's CE exit-code note) with the identical
three-error text seen locally, corroborating the local Debug build without
overruling it -- this is not a Debug-assert-only issue, so CE's Release
build is a meaningful independent witness here, not merely a corroboration
of "release builds are unaffected."

**Successor front end (Clang-based HLSL), tested because the maintainer
ties this issue's eventual resolution to Clang's C++ overload rules**:
`hlsl_clang_trunk` on the full three-line repro exits 1, stopping at the
first hard error (line 22, `t<uint>(5)`) before reaching line 23 (Clang
does not continue codegen after a Sema error the way dxc's diagnostics do
here). Isolating each call form individually
(`variant-clang-call1.hlsl` / `-call2.hlsl` / `-call3.hlsl`, each a single
line, `--source` override, archived as `manual-case-clang-call1-only.txt`
/ `-call2-only.txt` / `-call3-only.txt`) shows:

| call form | classic DXC (dxc_1_6_2112 / dxc_trunk) | hlsl_clang_trunk |
| --- | --- | --- |
| `t(5)` (implicit deduction) | errors | **compiles (exit 0)** |
| `t<uint>(5)` (template-id call) | errors | errors (different message: `'t' does not name a template but is followed by template arguments`) |
| `t.operator()<uint>(5)` (explicit member call) | errors | **compiles (exit 0)** |

Two of the reporter's three forms already compile under the Clang-based
front end, and the one that still fails (`t<uint>(5)`) is also the one
form the reporter said is *not* valid C++ ("in C++ `test(5)` passes ...
and `t.operator()<uint>(5)` passes as well" -- `t<uint>(5)` is conspicuously
not in that list). So Clang's current behaviour matches real C++ overload
resolution on this exact input: it accepts the two C++-legal forms and
rejects the one that is not C++ syntax at all. This is a genuine partial
answer to "has the successor already fixed this", worth surfacing, but it
does not change the verdict against classic DXC (`main`), which is what
this issue is filed against and which still rejects all three forms.

## Text staleness

No `text_stale` finding: the issue's body and both comments still describe
current behaviour accurately. The 2023-06-30 maintainer comment frames this
as a known limitation tied to a planned HLSL 202x overload-rules rewrite,
not a promise of an imminent fix, and nothing in the thread contradicts
what was measured.

## Verdict

`repros`, repro-quality `complete`, history `always-repro'd` (v1.6.2112,
the oldest release that can even parse `-HV 2021`, through v1.9.2607 and
`main-debug`), confidence high, suggested action `still-valid-keep-open`
(this is exactly the disposition the maintainer already gave it: a known,
tracked limitation awaiting the larger overload-rules rewrite, not
something to close).

Labels: no change proposed. Current `bug` + `hlsl-next` already describe
it correctly; `check-in-clang`'s description is a to-do ("see if this
repros in clang as well") and that comparison has now been run and
reported in this same triage pass, so per SKILL.md it should not be
proposed.
