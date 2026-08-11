# 4708 — "Free operator overload" — triage notes

Verdict: **`enhancement-not-bug`**, history **`never-implemented`**, confidence **high**.
`status=repros` in the narrow mechanical sense only — the reporter's shader is still
rejected by current DXC. That word is doing bookkeeping, not describing a defect. See
"Why not always-repro'd" below; it is the single most important thing on this page.

Ground truth: `main-debug` = `<repo>/build/Debug/bin/dxc.exe`, upstream commit
`13730886e6a9019e4e0823746470f3ab75341d6b`. The tree was checked against that commit with
`git diff --name-only 13730886e HEAD` excluding this skill's own directory: empty, and a
control diff against an older commit was non-empty, so the query can detect differences.
No compiler source was modified. (The binary self-reports a fork-local build id; the
upstream commit above is the citable one.)

## What was asked

The body is a question — "is this possible or is there another way around it? If not,
could this be a future feature?" — attached to a complete `cs_6_0` shader that declares a
class template `array<T,N>` with a member `operator[]`, then two **namespace-scope**
`operator+` templates, and evaluates `arr1 + 2.0f`.

## What current DXC does

`dxc -T cs_6_0 -E main -HV 2021 repro.hlsl` → exit `0x80004005` (E_FAIL). That is DXC's
ordinary "I diagnosed an error" status, **not** a crash; nothing here is crash-shaped and
no `internal_failure` predicate is involved.

```
repro.hlsl:15:12: error: overloading non-member 'operator+' is not allowed
array<T,N> operator+ (array<T,N> lhs, T rhs) {
           ^
repro.hlsl:34:35: error: scalar, vector, or matrix expected
    array<float, 3> result = arr1 + 2.0f;
                                  ^
```

The rejection is specific to *free operators*, and three controls on the same binary,
same flags, pin that down — each declared with `--expect no-match` and each compiling
cleanly (exit 0):

| control | difference from repro | result |
| --- | --- | --- |
| `control-member-operator.hlsl` | `operator+` is a **member** instead of free | compiles |
| `control-free-function.hlsl` | the free templates are named `add` instead of `operator+` | compiles |
| `control-hello.hlsl` | trivial shader | compiles |

So neither "free template" nor "operator overloading" is refused on its own. Only their
combination is. That is the issue, isolated to one variable.

## Why not `always-repro'd`

A linear bisect does report the reporter's shader failing on every release that can run it
(v1.6.2112 → v1.9.2607). Reporting that as `always-repro'd` would be false in substance,
for four independent reasons:

1. **The rejection is deliberate and asserted in-tree.** `tools/clang/test/SemaHLSL/v2021/
   operators/global-overload-disallowed.hlsl` exists specifically to require this
   diagnostic. DXC is behaving as its own test suite demands.
2. **The commit that added it says so.** `fb1f3036b` — "Error when declaring global
   operator overloads (#5796)", 2023-09-28, fixing #5792 — records that HLSL 2021 "can't
   resolve calls to global operator overloads and was never intended to support them, but
   it didn't error on them being declared." Never intended, not broken.
3. **The capability is still being designed.** hlsl-specs proposal *0008 Non-member
   Operator Overloading* was opened 2022-12-15 (two months *after* this issue), retargeted
   from 202x to 202y in April 2025, and marked **Accepted** in July 2025 with spec
   language landed. A feature with an accepted-but-unshipped spec has no "first broken
   release".
4. **The maintainer already said so in the thread**, on 2023-06-30.

`never-implemented` is the honest taxonomy value. Precedent in this workspace: issue 4501.

## The history scan, and the control that makes it mean anything

The symptom is a *diagnostic*, so a release predating HLSL 2021 emits its own unrelated
error and scores as a flawless reproduction. Bisect alone therefore cannot distinguish
"never implemented" from "always broken". `measure-releases.py` runs the **capability
control on every release**, and a release only counts if `control-member-operator.hlsl`
compiles there:

```
stable releases probed:        20
measurable (member-op ok):     16  v1.6.2112..v1.9.2607
of those, repro:               16
of those, free operator works: 0
```

v1.4.1907, v1.5.2010, v1.6.2104 and v1.6.2106 are **unmeasurable, not clean**: they reject
`-HV 2021`, and an appendix re-runs them without the flag, where they answer `'template'
is a reserved keyword in HLSL`. The construct could not be written at all before HLSL
2021, so no statement about free operators is possible for 2019–2021. 5 prereleases were
excluded by policy (the issue names none).

The instrument's self-test: on all 16 measurable releases the member-operator control
compiles while the repro fails, from the same binary with the same flags. The matrix can
tell the two arms apart.

### A second predicate dates a real, narrower change

`match-decl-diagnostic.json` has **inverted polarity** — it matches when DXC does the
*good* thing (diagnoses the bad declaration rather than only its use). It transitions
cleanly at **v1.8.2403**. A bisect prints that as `regressed-in`; the correct reading is
`diagnostic-added-in`, and it corresponds to `fb1f3036b` / #5796. Before v1.8.2403
(v1.6.2112–v1.7.2308) the declarations were accepted silently and only `arr1 + 2.0f` was
rejected, with the unhelpful `scalar, vector, or matrix expected`. This is a **diagnostic
quality improvement inside the never-implemented era**, not a behaviour regression, and it
is why the primary predicate deliberately does not key on message text.

## The successor compiler has already answered the design question

This was the highest-value measurement, and it inverts the issue's premise.
`hlsl_clang_trunk` on Compiler Explorer **compiles the reporter's shader unmodified**,
exit 0.

Because the reporter's `result` is dead, an accepting compiler produces an empty `main`,
which reads as "nothing happened". `repro-observable.hlsl` adds one store so the answer is
visible. Clang trunk emits:

```
call void @dx.op.bufferStore.f32(i32 69, %dx.types.Handle %1, i32 %2, i32 0,
                                 float 4.000000e+00, float undef, float undef,
                                 float undef, i8 1)
```

`2.0 + 2.0 = 4.0`, constant-folded **through the free `operator+`**. The operator was not
merely parsed; it was resolved and evaluated. This exact constant appears once in the
captured matrix and only from that source on that compiler (the `4.000000e+00` in
`hello`-derived output is `2.000000e+00`; attribution was checked line by line).

Clang is not taken at its word without controls. Same flags, five sources, four
compiler/arg combinations:

```
source             dxc_1_6_2112   dxc_trunk   clang   clang -fsyntax-only
repro              exit 5         exit 5      exit 0  exit 0
repro-observable   exit 5         exit 5      exit 0  exit 0
member-operator    exit 0         exit 0      exit 0  exit 0
free-function      exit 5         exit 0      exit 0  exit 0
hello              exit 0         exit 0      exit 0  exit 0
```

Clang compiles the trivial control and the member-operator near miss, so its acceptance of
the free operator is a real difference and not an artefact of partial HLSL support. The
direction of the difference also matters: here the *successor accepts* and DXC rejects,
which is the safe direction — an erroring Clang pane would have needed much more care.

Link: **https://godbolt.org/z/9esTrW5ox** (3 panes; read back via `api/shortlinkinfo` and
compiler ids and args verified after publishing).

One caveat, recorded rather than smoothed over: this measures that Clang's HLSL front end
*accepts* the construct. It does not by itself prove the acceptance is a deliberate
implementation of proposal 0008 rather than inherited C++ overload-resolution behaviour.
No tracking issue was found in `llvm/llvm-project` by search. A maintainer should treat
the Clang result as an observation to confirm, not as a shipped-feature claim.

## Thread accuracy

The reporter's text is accurate and needs nothing. The one standing maintainer comment
names **HLSL 202x**; the accepted proposal now targets **202y** (retargeted 2025-04-01,
accepted 2025-07-22). Recorded as `text_stale` narrowly on that point only — the substance
of the comment ("almost certainly going to make the cut") turned out right.

## Caveats

- On **v1.6.2112** the `free-function` control fails with `function template partial
  specialization is not allowed` — two overloaded free function templates, unrelated to
  operators, fixed by v1.7.2207. The *capability* control (member operator) still passes
  there and that release's repro error is at the use site, so its declarations parsed and
  the row remains measurable. The narrower "it isn't free templates" claim just isn't
  available on that one release.
- Nothing before v1.6.2112 can be measured, in either direction.
- Whether Clang's behaviour is intentional is unconfirmed (above).
