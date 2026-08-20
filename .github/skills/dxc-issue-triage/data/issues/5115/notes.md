# Notes -- #5115 "signed/unsigned overload resolution error seems unjustified"

## Ground truth

`main-debug`, upstream commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df` ("[HLSL] Add LinAlg
descriptor I/O offset, stride and layout coverage (#8762)"). The local binary self-reports
`dxcompiler.dll: 1.10(5465-7665270b)(1.9.0.5465) - 1.9.0.5465 (triage, 7665270b9)` -- a
different commit and branch name, because this is a working-tree build on the triage branch,
not a checkout of upstream `main`. This is **expected**, not a discrepancy: the tree the binary
was built from is verified byte-identical to the cited upstream commit outside this skill
directory:

```
git diff --name-only 7665270b9 89e2f98e29c289ae8ad9e00dd310104fea9fd7df
  -> 0 files outside .github/skills/dxc-issue-triage/
```

Control (an older commit that must, and does, show unrelated changes):

```
git diff --name-only 7665270b9 13730886e6a9019e4e0823746470f3ab75341d6b
  -> 33 files outside .github/skills/dxc-issue-triage/
```

So "no differences outside the skill directory" is a real result here, not a query that could
not have detected any -- confirming the registered `main-debug` compiler is ground truth for
upstream commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.

## The repro

`repro.hlsl` is the issue's first program verbatim (`void f(unsigned int){}` / `void
f(int){}`, called as `f(1);`). `cmd.txt` is `-T ps_6_0 -E PSMain repro.hlsl`, matching the
Compiler Explorer permalink in the issue body (a pixel shader entry point; the construct is not
stage-specific, but the reporter's own example uses `SV_TARGET`, so that is what was kept).

Running it against `main-debug` reproduces the exact reported diagnostic, verbatim down to the
column numbers (`out-main-debug.txt`):

```
repro.hlsl:6:5: error: call to 'f' is ambiguous
    f(1);
    ^
repro.hlsl:1:6: note: candidate function
void f(unsigned int){}
     ^
repro.hlsl:2:6: note: candidate function
void f(int){}
     ^
```

`control-unsigned-literal.hlsl` is the issue's second program (`f(1u);`), run with
`--expect no-match`: it compiles cleanly on `main-debug` (`variant-unsigned-literal-main-debug.txt`,
exit 0, valid DXIL emitted), exactly as the issue reports. This confirms the predicate does not
just fire on every call to `f`.

`match.json` anchors on the literal diagnostic text plus both candidate-function notes (see its
`note` field for the full reasoning); this is a diagnostic-quality issue, so the symptom *is*
the diagnostic and the exit code (E_FAIL either way) cannot discriminate it from an ordinary
diagnosed error.

## History

`bisect` (binary search, both endpoints agree) and `bisect --linear` (full 20-release linear
scan, since the maintainer comment gives no reason to expect a fix/revert, this was run anyway
as a due-diligence check) both report **always-repro'd across v1.4.1907 (2019-07) .. v1.9.2607
(2026-07)** -- every stable release, 0 invalid probes. int/unsigned overloading and integer
literals are not a feature that postdates any of these releases, so there is no
feature-absence trap to check for here (this is not a `lib_6_x`/profile-gated construct);
every probeable release actually exercised the code under test. `main-debug` itself also
reproduces. The issue was filed 2023-03-25; v1.7.2212 (the release current at filing) is
inside the always-repro'd range. There is no evidence anywhere in the thread of a fix attempt,
a revert, or a re-opening for this specific case, so a hidden non-monotonic window was not
expected -- and the linear scan confirms there isn't one.

## Compiler Explorer

Published: https://godbolt.org/z/xPz8ndv7T (`dxc_1_6_2112`, `dxc_trunk`, `hlsl_clang_trunk`;
full panes in `manual-case-godbolt-verify.txt`).

- `dxc_1_6_2112` and `dxc_trunk` both reproduce the exact diagnostic (exit 5).
- `hlsl_clang_trunk` (the new Clang-based HLSL front end, `clang version 24.0.0git
  ecdcdf0577c18c327c5883d0fc1cee36a5cc6f1c`) **compiles the identical source with no
  diagnostic at all** and emits valid DXIL (exit 0). This corroborates, on the successor
  compiler, exactly what the maintainer's 2023-06-30 comment predicted: "[the HLSL 202x
  overload-rules rewrite] is effectively going to result in us adopting C++ overload rules
  completely for HLSL, which should solve this."

Before trusting that cross-compiler difference, two checks (per SKILL.md step 7's warning that
a Clang difference is not evidence without a control):

1. **The pixel-stage backend genuinely lowers this shader in Clang** -- it is not a case where
   Clang fails to lower `SV_Target` and the "success" is spurious. The pane's DXIL is complete
   and well-formed (`storeOutput` writes for all 4 components, valid `dx.entryPoints`/
   `dx.shaderModel` metadata), so the difference is about overload resolution, not about
   stage support.
2. **Clang's ambiguity detector is not simply silent for every call.**
   `control-genuine-ambiguity.hlsl` keeps the same two overloads and calls `f(1.0f)` instead --
   a call that *is* genuinely ambiguous under real C++ rules (`float`->`int` and
   `float`->`unsigned int` are both floating-integral conversions of equal rank). Both
   `main-debug` (run locally, `--expect match`, `variant-genuine-ambiguity-main-debug.txt`) and
   `hlsl_clang_trunk` (published alongside `dxc_trunk`, archived in the content-hashed
   `manual-case-godbolt-verify-78501709fccc.txt`) reject it with the **identical** message
   shape (`error: call to 'f' is ambiguous` plus both candidate notes) -- so Clang's overload
   resolution is exercising the same diagnostic path and correctly reports ambiguity when the
   ambiguity is real; it is not merely permissive. That both front ends print byte-identical
   wording for the genuinely-ambiguous case, while disagreeing only on the reported (spurious)
   one, is itself evidence that the difference is specifically in the *ranking* of an
   integer-literal argument against `int`/`unsigned int` overloads, not in diagnostic
   formatting or general permissiveness.

(`manual-case-godbolt-verify-c8707055f79a.txt` is the auto-archived copy of the primary-repro
panes from before the control run; both archives and the current file are on disk.)

## Source-side look (partial, not load-bearing)

`GetConversionRank` in `tools/clang/lib/Sema/SemaOverload.cpp` -- the table mapping
`ImplicitConversionKind` to a rank used for "which candidate is better" -- has HLSL-specific
additions (search `// HLSL Change` in that function) but the *generic* C++ integral-conversion
entry is unmodified from upstream Clang and would already rank an `int`->`int` identity
conversion (`ICR_Exact_Match`) strictly better than `int`->`unsigned int`
(`ICR_Conversion`), which is what C++ (and gcc12, per the issue's own second godbolt link)
does. That means the generic table is not, by itself, the site of the bug; something
upstream of it (most plausibly how a plain, unsuffixed integer literal's type is treated when
building the candidate/argument conversion in the first place) must be scoring the `f(1)`
argument as equally good against both overloads. This was not traced to a specific commit or
function -- doing so would need building an instrumented compiler, which is out of scope for
this triage -- so it is reported as a plausible direction, not a proven root cause. The
maintainer's own comment already gives the accepted explanation ("broken behavior in DXC's
overload resolution") and the planned fix (adopting C++ overload rules via the HLSL 202x
`const`-instance-methods proposal), which is corroborated above by `hlsl_clang_trunk` already
implementing corrected behaviour for this exact case.

## Timeline

`gh api repos/microsoft/DirectXShaderCompiler/issues/5115/timeline` returns no
`cross-referenced` events at all (only `labeled`/`milestoned`/`commented`/project-board
events, all from 2023-06-29/30). No duplicate or successor issue was found this way.

## Assessment

`repros`, repro quality `complete`, history `always-repro'd` (v1.4.1907..v1.9.2607, plus
`main-debug`), confidence `high`. The issue's own text is not stale: the maintainer's comment
already correctly diagnoses this as current, acknowledged behaviour with a known (if
long-range) remediation path, and nothing in the thread claims it was ever fixed. Suggested
action: `still-valid-keep-open` -- the maintainer has already scoped the actual fix to a
larger, tracked language-rules rewrite (not a quick patch), so there is no smaller fix to
request, and the issue is correctly triaged as `hlsl-next` already. The new value this triage
adds is (1) a captured, always-reproducing 20-release + main-debug history for a report that
had no history evidence before, and (2) direct confirmation that the Clang-based successor
front end has already implemented the corrected behaviour for this specific input, which is
new, useful, and previously unverified information for this issue.
