# #5395 -- Report warning when loop variable shadows one from outer scope in HLSL 2021

## Summary

Filed 2023-07-06. Claim: pre-2021, a `for`-loop induction variable that shadows a
variable already declared in the enclosing scope produces
`warning: redefinition of 'i' shadows declaration in the outer scope; most recent
declaration will be used [-Wfor-redefinition]`. With `-HV 2021`, the identical source
produces no such warning.

**Verdict: `repros`.** The described absence is real and reproduces on every DXC release
that supports `-HV 2021` (v1.6.2112, 2021-12-08, through v1.9.2607, 2026-07-29) and on
`main-debug` (89e2f98e2, 2026-08-19). It is not a regression in the warning logic, though:
it is a designed consequence of HLSL 2021 switching the `for`-loop's induction variable to
real block scoping, which removes the same-scope name conflict this specific warning exists
to soften. See "Root cause" below.

## Repro

`repro.hlsl` / `cmd.txt`: the issue's own shader, verbatim, compiled with
`-T ps_6_6 -HV 2021 repro.hlsl` (also the issue's own `RUN:` line).

```hlsl
float4 main(float f: F) : SV_Target {
       uint i = 7;
       for (uint i = 0; i < 3; i++) {
         f += i;
       }
       return f + i;
}
```

## Ground truth measurement

`main-debug` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df, self-reports
`1.9.0.5465 (triage, 7665270b9)` -- local HEAD `ced72eee3` is a descendant of the ground-truth
commit and `git diff --name-only 89e2f98e2 HEAD` touches nothing outside
`.github/skills/dxc-issue-triage`, so the binary is a faithful build of that commit):

- `out-main-debug.txt`: `-HV 2021`, exit 0, **no** `-Wfor-redefinition` warning, DXIL emitted
  normally -> scored `repro` by `match.json`.
- `variant-hv2018-control-main-debug.txt` (`--expect no-match`, satisfied): the identical
  source under `-HV 2018` **does** print the warning, confirming the predicate can detect it
  when present.
- `variant-hv2016-control-main-debug.txt` (`--expect no-match`, satisfied): same, under
  `-HV 2016`.

Interesting side observation, not part of the reported symptom: the *value* used for the
final `f + i` differs between language modes (`main-debug`'s HV2021 run folds to
`fadd fast float %1, 1.000000e+01` i.e. +10, HV2018's to `+6.000000e+00`). That is expected
and correct: under HV2021's real block scoping the outer `i` (7) survives the loop and is
what `return f + i` reads (`f` accumulates `0+1+2=3` inside the loop, so `f+3+7 = f+10`);
under the pre-2021 "redefinition" semantics the loop's `i` *is* the same storage as the outer
one, so after the loop it holds the loop's last value (3), giving `f+3+3 = f+6`. This is not
a new finding for this issue (the issue is only about the missing warning, not about the
values), but it is worth recording because it shows the two language modes are not merely
suppressing a warning on the same underlying semantics -- HV2021 has already changed what the
program *means*, correctly, before the diagnostic question is even asked.

## Root cause (read from source, not just observed)

`tools/clang/lib/Parse/ParseStmt.cpp` (`ParseForStatement`):

```cpp
// HLSL Change Starts - leak declarations in for control parts into outer scope
if (getLangOpts().HLSLVersion < hlsl::LangStd::v2021) {
  ScopeFlags = Scope::ForDeclScope;
}
// HLSL Change Ends
```

Only pre-2021 language modes mark the for-loop's `Scope` as `ForDeclScope`. In
`Sema::HandleDeclarator` (`tools/clang/lib/Sema/SemaDecl.cpp:4783`):

```cpp
ShadowMergeState MergeState = S->isForDeclScope() ?
  ShadowMergeState_Possible : ShadowMergeState_Disallowed; // HLSL Change
```

`ShadowMergeState_Possible` is what lets `MergeVarDeclTypes` (`SemaDecl.cpp:3511-3516`,
`3559-3563`) treat the loop's `i` as a *redeclaration* of the outer `i` in the same scope
(instead of a hard `err_redefinition`) and emit `warn_hlsl_for_redefinition` ("redefinition of
%0 shadows declaration in the outer scope; most recent declaration will be used",
`DiagnosticSemaKinds.td:7808`, group `HLSLForRedefinition` / `-Wfor-redefinition`). This is a
legacy-compatibility diagnostic for the pre-2021 behaviour of "the loop variable leaks into
the enclosing scope and reuses the same storage as the identically-named outer variable" --
it exists to soften what would otherwise be a same-scope `error: redefinition` down to a
warning, and to say plainly that the two declarations merge into one.

With `-HV 2021`, `ForDeclScope` is never set, so the loop's `i` lives in a genuine nested
scope. Name lookup for a previous declaration never finds the outer `i` as being in the same
declarative region, so `HandleDeclarator`'s merge path is not entered at all for this
declaration -- there is no "redefinition" event for `warn_hlsl_for_redefinition` to describe,
because under real block scoping this is ordinary shadowing, not redeclaration.

**DXC does not have a general "-Wshadow"-style warning for ordinary block-scope shadowing in
any language mode.** Confirmed with a hypothesis-labelled control (`control-block-shadow.hlsl`,
an inner `{ }` block, not a loop, redeclaring `i`): compiling it under both `-HV 2021`
(`variant-block-shadow-hv2021-main-debug.txt`) and `-HV 2018`
(`variant-block-shadow-hv2018-main-debug.txt`) produces **no** warning at all, exit 0, in
either mode. So `-Wfor-redefinition` was never a general shadow-detection feature; it was
narrowly the softened-error-message for the pre-2021 for-loop leak quirk, and that specific
quirk is precisely what HLSL 2021 removed by design.

**What this means for the verdict:** the reported absence is completely real and the issue's
one-line summary is accurate as a description of current behaviour. But it is not evidence of
a broken diagnostic that used to fire and stopped; it is the necessary corollary of a deliberate
language-semantics fix (real block scoping), and there was never a general shadow diagnostic to
"lose" for this case. What would resolve the issue is a *new* diagnostic -- some form of
`-Wshadow` for HV2021+ that flags ordinary block/loop shadowing -- rather than restoring
old behaviour, which would be a regression of the very language change referenced by this
issue's own `hlsl2021` label.

## History

`bisect --linear` (only `--linear` used; monotonicity was not assumed given `HV` acceptance is
gated by release, and this also serves as a population census of every release that can even
accept `-HV 2021`):

```
v1.4.1907      invalid-probe  ("Unknown HLSL version: 2021" -- HV2021 not implemented yet)
v1.5.2010      invalid-probe  (same)
v1.6.2104      invalid-probe  (same)
v1.6.2106      invalid-probe  (same)
v1.6.2112      repro          (2021-12-08 -- first release accepting -HV 2021)
v1.7.2207 .. v1.9.2607   repro   (every one of the remaining 15 probeable stable releases)
main-debug     repro
```

Skipped from the search: `v1.2.0-alpha` (no usable `dxc` asset) and, by policy, 5 prereleases
(`v1.5.2003`, `v1.8.2306-preview`, `v1.8.2405-mesh-nodes-preview`, `v1.10.2605.2`,
`v1.10.2605.24`) -- none is named by the issue text, so none is opted in via
`release-policy.json`.

**"Always-repro'd" here means: reproduces on every release that has ever supported `-HV
2021`, without exception**, i.e. since the very first release capable of running this repro
at all -- there is no fixed window and no regression; the language mode postdates this
specific warning question entirely. The report itself was filed 2023-07-06 (against
`dxcompiler.dll 1.7 - 1.7.0.3942`), between the build dates of v1.7.2212.1 (2023-03-01) and
v1.7.2308 (2023-08-14), both of which scored `repro` -- squarely inside the always-repro'd
range.

## Compiler Explorer

https://godbolt.org/z/KzYb6cKTE (`dxc_1_6_2112` -- CE's oldest, and not coincidentally the
exact release that introduced `-HV 2021` support -- and `dxc_trunk`). Both panes compile
cleanly, exit 0, with no shadow-redefinition warning. `godbolt-note.txt` explains what to look
for and points the reader at the `-HV 2018` control and the `ParseStmt.cpp` source location.
Link verified by short-link read-back (no mismatch warning from `triage.py godbolt`); full
pane text archived in `manual-case-godbolt-verify.txt`.

Note: `dxc_trunk`'s emitted debug-info metadata for the loop shows less detail than
`dxc_1_6_2112`'s (only one `DILocalVariable` for `i`, versus a distinct lexical-block-scoped
one for the loop's `i` in 1.6.2112); this is a debug-info generation difference, unrelated to
the reported symptom, and not further investigated here since it's outside what this issue is
about.

## Labels

Current: `bug`, `hlsl2021` (both accurate: this is squarely about HLSL 2021 behaviour, and
"missing diagnostic that a user reasonably expects" is a defensible bug report even though the
underlying mechanism is legacy-specific -- see suggested action below for the nuance).

Proposed add: `diagnostic` (the issue is precisely and only about a compiler diagnostic that
does/doesn't fire; this is the routing label for that class of issue and none of the existing
labels capture it).

No removal proposed. `bug` is left in place: while the root-cause analysis above supports
recharacterising this as a request for a *new* diagnostic rather than a regression, that is a
policy call for a maintainer, not evidence this triage can settle unilaterally, and the label
itself is not falsified by the finding.

## Text staleness

None. The issue's title and body remain an accurate description of current behaviour; nothing
in it needs correction.

## What was not, and could not be, measured here

- No maintainer or reporter comments exist on the issue (0 comments) and no
  cross-reference timeline events exist (checked via
  `gh api repos/microsoft/DirectXShaderCompiler/issues/5395/timeline`), so there is no prior
  discussion to reconcile against.
- This is a pure diagnostic-emission question, fully decidable from `dxc` output; no
  not-compiler-verifiable aspect was identified.
