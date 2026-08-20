# Issue #5674 — notes

## Summary

The repro is exact and minimal: declare a global variable literally named `matrix`
(`float2x2 matrix;`), then use it as an operand of `*` (`float2(1,2) * matrix`). This crashes
`dxc` with an access violation instead of compiling or producing an ordinary diagnostic.
Confirmed reproducing on `main-debug` (89e2f98e29c289ae8ad9e00dd310104fea9fd7df — verified via
tree-diff: 0 files outside `.github/skills/dxc-issue-triage` differ between `main-debug`'s HEAD
and this commit).

```
$ dxc -T cs_6_0 repro.hlsl
Internal compiler error: access violation. Attempted to read from address 0x0000000000000038
```
(`out-main-debug.txt`, exit 3221225477 = 0xC0000005.)

This is byte-identical in wording to the reporter's own v1.7.2308.7 output.

## Predicate

`match.json` uses `internal_failure` (exit-code based), not text matching — per SKILL.md
guidance for any crash-shaped issue, since the same defect can present with or without a
message across builds/platforms.

## Control

`control-no-shadow.hlsl` is the identical shader with the variable renamed to `mymatrix`
(no longer shadowing the builtin). It compiles down to ordinary diagnostics (E_FAIL,
`variant-no-shadow-main-debug.txt`, exit 2147500037): "HLSL requires a type specifier for all
declarations" (because the repro's `main()` also has no return type — a pre-existing, unrelated
issue with the reporter's minimal repro) and "cannot convert from 'float2x2' to 'float2'" (the
`*` here is a component-wise/outer op producing a matrix, not a real matrix-vector product,
consistent with `matrix`/`vector` operator overload behavior). No crash. This isolates the
defect to the identifier collision with the built-in `matrix` template name, not to the
malformed `main()` signature, which is present in both the crashing and non-crashing shaders.

## History (`bisect`, binary search, no `--linear` needed — clean monotonic transition)

```
v1.4.1907   no-repro   (out-v1.4.1907.txt)
v1.6.2112   no-repro   (out-v1.6.2112.txt)
v1.7.2207   repro      (out-v1.7.2207.txt)
v1.7.2212   repro
v1.8.2403   repro
v1.9.2607   repro
```
Result: **regressed-in v1.7.2207** (last good: v1.6.2112). No releases were skipped as
`invalid-probe`/prerelease inside the transition interval; the two endpoints and the
transition release were probed directly and disagreed cleanly.

v1.4.1907 and v1.6.2112 do **not** treat this as `invalid-probe` — they give an ordinary
diagnosed rejection of the *declaration itself*:

```
repro.hlsl:1:10: error: template specialization requires 'template<>'
float2x2 matrix;
         ^~~~~~
template<>
repro.hlsl:1:10: error: no variable template matches specialization
...
repro.hlsl:6:29: error: cannot refer to class template 'matrix' without a template argument list
```

i.e. before the regression, DXC never let `matrix` be redeclared as a variable name at all —
it rejected the source outright, and the crash could never be reached from that state. This
is a real semantic transition (a template name became shadowable), not a demoted probe.

## Attribution

The `v1.6.2112..v1.7.2207` window holds 248 commits. `git log --oneline v1.6.2112..v1.7.2207
-- tools/clang/lib/Sema/SemaOverload.cpp tools/clang/lib/Sema/SemaLookup.cpp
tools/clang/lib/Sema/SemaTemplate.cpp` narrows that to 4 commits touching name-lookup/overload
code; one of them, `a7fa058dd` ("Rework name lookup (#4332)", 2022-04-12), is the standing
candidate. Its own commit message states the change directly:

> "HLSL allows omit[t]ing empty template argument lists for default template cases (i.e.
> `matrix` is valid in HLSL, but in C++ it would need to be `matrix<>`). This patch should
> fully resolve that case."

`git merge-base --is-ancestor a7fa058dd v1.7.2207` exits 0 (in); the same check against
`v1.6.2112` exits 1 (not in) — consistent with the observed transition. This is a strong,
not proven, attribution: the commit is confirmed inside the window and its own description
matches the observed behavior change (declaring `matrix` without `<>` stopped being an
outright parse-time rejection), but the crash itself was not built and tested at that exact
commit in isolation.

## Crash location

`cdb -c "g;kn 40;q"` on `main-debug` (`manual-case-assert-stack.txt`) shows the access
violation inside `clang::ValueDecl::getType`, reached from
`Sema::ArgumentDependentLookup` -> `Sema::FindAssociatedClassesAndNamespaces`, called from
`Sema::CreateOverloadedBinOp` while resolving the `*` operator. This is consistent with the
name-lookup rework: once `matrix` can name a variable, overload resolution for `operator*`
performs ADL over that operand and dereferences something invalid (offset `+0x38` off a
null/bad pointer) — plausibly because the `ValueDecl` on the `matrix` identifier is left in
some partially-formed state given the ambiguity with the built-in template name. This was not
independently re-derived by building the isolated commit; the stack is offered as corroborating
evidence of *where*, not a proof of the exact root cause line.

## Compiler Explorer

https://godbolt.org/z/bsEPd3eaY — `dxc_1_6_2112` (CE's oldest) cleanly rejects the
declaration (`template specialization requires 'template<>'`); `dxc_trunk` crashes with
`SIGSEGV` (Linux equivalent of the Windows access violation). Read-back matched what was sent;
full panes saved in `manual-case-godbolt-verify.txt`.

## Labels

Current: `bug`, `crash`, `incorrect-code`. Proposing to add `matrix-bug` (label description:
"Bugs relating to matrix types") — this crash is specifically about the built-in `matrix`
identifier colliding with a user declaration during matrix-operator overload resolution, which
is exactly what that label is for. Not proposing removal of any current label: `bug`/`crash`
are clearly correct, and while it's debatable whether shadowing a builtin template name still
counts as "incorrect code" post-regression, that is a judgment call about intended HLSL
semantics and not something the evidence here settles, so it is left alone.

## Text staleness

None found: the issue text (title, body) still accurately describes current behavior. The
title says "Crash in syntax check when using 'matrix' keyword in an operation" — the crash is
in fact in Sema/overload resolution rather than lexical "syntax check", but the report itself
never claims a specific compiler stage beyond that generic framing, and it isn't otherwise
inaccurate.

## What could not be determined

- No independent isolated build at `a7fa058dd` (and its parent) was performed to prove the
  attribution beyond "confirmed inside the window, and the commit's own description matches
  the observed transition." Per SKILL.md this keeps the attribution "strong, not certain."
- Whether shadowing `matrix` was an *intended* consequence of the name-lookup rework (as
  opposed to only intending to allow bare `matrix`/`vector` as a *type* reference) is not
  something this triage can settle from the commit message alone; it reads compatibly with
  either reading.
