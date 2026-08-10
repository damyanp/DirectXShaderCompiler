# #4096 — `bool` cast operator doesn't implicitly trigger

**Status: `repros`** on a clean Debug build of `main` at `13730886e`
(`dxc --version` → `1.9.0.5433`; the binary self-reports the fork-local merge
`ab5400907`, which resolves nowhere public — the source is identical to `13730886e`
outside the triage skill directory, verified with a controlled `git diff`).

Filed 2021-11-22 by llvm-beanz. `hlsl2021` at filing, relabelled `hlsl-next` 2022-10-04
by pow2clk, milestoned **HLSL 202x** 2023-06-30. Two comments, no linked fix.

## Repro

`repro.hlsl` is the issue body verbatim. `cmd.txt`:

```
-T cs_6_0 -E main -HV 2021 repro.hlsl
```

The reporter gave no command line. `-T cs_6_0 -E main` follows from the `[numthreads]` entry
point. `-HV 2021` is pinned because member `operator` declarations are an HLSL 2021 feature;
it is today's default, so it changes nothing on `main`, but it makes every release in the
sweep answer the same question and makes pre-2021 releases say so explicitly rather than
failing with an unrelated parse error.

Repro quality: **complete**.

## Ground truth

```
$ dxc -T cs_6_0 -E main -HV 2021 repro.hlsl
repro.hlsl:3:3: error: conversion operator overloading is not allowed
  operator bool() {
  ^
repro.hlsl:11:7: error: value of type 'Foo' is not contextually convertible to 'bool'
  if (A)
      ^
[exit] 2147500037 (0x80004005, E_FAIL — an ordinary diagnosed error, not an internal failure)
```

`out-main-debug.txt`. The second error is the reported symptom, unchanged since the issue was
filed. The first is new (see "What changed").

## Predicates

`match.json` — `any_of` of two positive strings, one defect with two signatures across time:

1. `is not contextually convertible to 'bool'` — the declaration is accepted and the `if` is
   then rejected, because the operator is never considered for the contextual conversion.
2. `conversion operator overloading is not allowed` — the declaration itself is refused, so
   the operator cannot trigger at all.

Neither clause is an absence clause, so the predicate cannot be satisfied for free by a run
that failed early. `nonzero_exit` is deliberately unused: on Windows every diagnosed error
exits E_FAIL, so it would match a correct rejection just as readily.

`match-decl-rejected.json` — clause 2 alone, bisected separately to date the shape change.

**Known limit, recorded rather than hidden.** A build that silently substituted HLSL's flat
conversion for the operator in an `if` would satisfy neither clause and would score no-match
on this repro, because `Foo A = {1}` makes `x < 5` and `bool(x)` agree and the shader has no
observable. No probed build behaves that way; `case-if-discriminating.hlsl` and
`case-cstyle-cast.hlsl` measure that form directly (below).

## Controls (all captured)

| file | expect | result on `main` |
| --- | --- | --- |
| `control-no-operator.hlsl` — struct with the operator removed, `if (A.x < 5)` written out | `no-match` | exit 0, clean DXIL |
| `control-method-call.hlsl` — operator replaced by an ordinary `bool asBool()` member, `if (A.asBool())` | `no-match` | exit 0, clean DXIL |
| `control-hlsl2021-presence.hlsl` — smallest shader that still asks for `-HV 2021` | `no-match` | exit 0 |
| `control-rwbuffer-only.hlsl` — the `RWBuffer` store with no struct and no cast | `no-match` | exit 0 |
| `case-cstyle-cast.hlsl` — operator + explicit `(bool)A`, result observable | `match` | rejected at the declaration |
| `case-if-discriminating.hlsl` — the reporter's `if (A)` with the result observable | `match` | both errors |

`control-method-call.hlsl` is the load-bearing one: it proves the struct, the member function
and the `if` all work, and that the only thing failing is the *implicit conversion*.

## Release history

`bisect --linear`, 20 stable releases, `match.json`:

**`always-repro'd` across v1.6.2112 (2021-12-08) .. v1.9.2607 (2026-07-29)** — 16 releases,
every one of them. Four older releases (v1.4.1907, v1.5.2010, v1.6.2104, v1.6.2106) are
`invalid-probe`: they answer `dxc failed : Unknown HLSL version: 2021`. That demotion is not
taken on trust — `manual-case-release-matrix.txt` runs `control-hlsl2021-presence.hlsl` on
**every** release, and those four reject the trivial shader too, so the rejection is about the
language mode and not about the repro. Five probeable prereleases were excluded from the
search by policy (v1.5.2003, v1.8.2306-preview, v1.8.2405-mesh-nodes-preview, v1.10.2605.2,
v1.10.2605.24).

`bisect --linear` with `match-decl-rejected.json`: no-repro on v1.6.2112 .. v1.9.2602.24,
**repro at v1.9.2607**.

**The issue predates every probeable release.** It was filed 2021-11-22; v1.6.2112 shipped
2021-12-08. No stable release can reproduce the reporter's own build, so "always reproduced"
means "for as long as it is possible to check", which here is from the first stable release
that can express HLSL 2021 onwards.

## Was the operator ever invoked?

The reporter's shader cannot say. `case-cstyle-cast.hlsl` makes the two candidate conversions
disagree — `operator bool() { return x > 5; }` with `x == 1` is false, HLSL's flat conversion
`bool(1)` is true — and stores 222 or 111 accordingly. On all 15 releases from v1.6.2112 to
v1.9.2602.24 the emitted DXIL is
`bufferStore(..., i32 111, i32 111, i32 111, i32 111, i8 15)`: the flat conversion, every
time. The operator body has never run in any shipped compiler that accepted the declaration.
Full transcript with echoed argv in `manual-case-release-matrix.txt`.

## What changed

`err_hlsl_unsupported_conversion_operator` — "conversion operator overloading is not allowed"
— was added by **PR #8206, commit `b13e386be`** (Damyan Pepper, 2026-04-14), in
`Sema::CheckConversionDeclarator` (`tools/clang/lib/Sema/SemaDeclCXX.cpp:6961` at
`13730886e`). Attribution is strong: `git merge-base --is-ancestor` puts it inside v1.9.2607
and outside v1.9.2602.24, and it is the **only** one of the 224 commits in that window that
touches `SemaDeclCXX.cpp`. It is documented in `docs/ReleaseNotes.md:175`.

This is not a fix for #4096 and must not be recorded as one — the construct now fails earlier
rather than working. It does change what a reader of the issue sees today: the example is
rejected at the declaration as well as at the `if`.

## Root cause

llvm-beanz's 2023-02-08 comment pointed at `SemaOverload.cpp` line 1136. That line is still
exactly the guard at `13730886e`:

```cpp
if (SuppressUserConversions || S.getLangOpts().HLSL) { // HLSL Change - no user conversions
```

`TryUserDefinedConversion` returns a bad conversion sequence unconditionally in HLSL, which is
why no user-defined conversion is ever considered — and why the diagnostic is the generic
"not contextually convertible" rather than anything about the operator.

## Compiler Explorer

https://godbolt.org/z/6Y38q1bn9 — `dxc_1_6_2112`, `dxc_trunk`, `hlsl_clang_trunk`, verified
by reading the shortlink back (`/api/shortlinkinfo/`: three panes, arguments as sent).
Full pane text in `manual-case-godbolt-verify.txt`. CE runs Linux Release builds; exit 5 there
is E_FAIL truncated to its low byte.

- `dxc_1_6_2112` → one error, on the `if`.
- `dxc_trunk` → that error plus the declaration error. Corroborates the local Debug build.
- `hlsl_clang_trunk` → **exit 0**. Clang's HLSL front end accepts the source.

## Clang comparison

Clang accepting the reporter's shader is not by itself an answer: its body is dead code, so an
empty `main()` cannot say whether Clang *invoked* the operator. `case-if-discriminating.hlsl`
attaches an observable to the reporter's own `if (A)` construct
(`manual-case-clang-discriminating.txt`, generated by `probe-clang.py`, every request echoed):

| source | `dxc_1_6_2112` | `dxc_trunk` | `hlsl_clang_trunk` |
| --- | --- | --- | --- |
| `case-if-discriminating.hlsl` (`if (A)`) | rejected | rejected | exit 0, **stores 222** |
| `case-cstyle-cast.hlsl` (`(bool)A`) | exit 0, stores 111 | rejected | exit 0, stores 111 |
| `control-no-operator.hlsl` | — | — | exit 0 |
| `control-rwbuffer-only.hlsl` | — | — | exit 0 |

`222` is the operator's answer (`1 > 5` is false), constant-folded into
`bufferStore(..., i32 222, ...)`. **Clang invokes the user-defined `operator bool()` in an
`if` condition — the exact behaviour this issue asks for.** The two controls rule out the
alternative readings: Clang is not failing on `RWBuffer` and not failing on the shader shape,
so its acceptance is about the conversion.

The C-style-cast row is a separate observation and is *not* what this issue reports: for
`(bool)A`, Clang currently does the same flat conversion the older DXC releases do.

## Assessment

The reported symptom is present on every stable release that can compile the input and on
`main`. Nothing has been fixed. What has changed is the shape of the failure, at v1.9.2607.

The remaining question is not "does it still reproduce" — it does — but where the work belongs
and whether DXC should track it, given that (a) DXC now rejects the declaration outright, (b)
the enabling change is a language-version item, and (c) the successor front end already
implements it. That is a product and language decision, so the suggested action is
`needs-human-judgement` rather than a triage conclusion.

On (b), the design position is already on record. This issue is labelled `hlsl-next` and
milestoned **HLSL 202x**, and llvm-beanz wrote on `microsoft/hlsl-specs` PR #37
([discussion_r1158553249](https://github.com/microsoft/hlsl-specs/pull/37#discussion_r1158553249),
2023-04-05), about adding operators to built-in types:

> those operators will be HLSL 202x features, not available in the older language versions.
> There are some other changes that are planned for 202x which will require significant
> reworking of overload resolution (see: https://github.com/microsoft/hlsl-specs/pull/34), and
> I think that we should expect that adding new operator overloads will depend on that.

llvm-beanz cross-referenced #4096 into that PR the next day (2023-04-06T14:00:38Z). I could
not find text containing "4096" in PR #37's current comment bodies, so the cross-reference
event is the link I can evidence; the quotation above is verified verbatim and is the clearest
statement of where this belongs. The issue was milestoned HLSL 202x on 2023-06-30, after that
exchange. No DXC PR has ever been linked to #4096.

**Not marked `text_stale`.** The body still describes what the compiler does: the example does
not work, for the reason given. A reader spot-checking it today gets *more* errors, not fewer,
so they cannot wrongly conclude "cannot reproduce" — which is the harm that field exists to
flag. llvm-beanz's floating link to `SemaOverload.cpp` line 1136 still lands on the right
line, checked at `13730886e`.

## Labels

Now: `hlsl-next`. Proposed additions: `type-system` (the defect is that
`TryUserDefinedConversion` is disabled wholesale for HLSL, an inconsistency in the type
system's conversion rules) and `enhancement` (it has never worked in any release that can
express it, and the enabling change is a language-version feature, not a regression). No
removals. `check-in-clang` deliberately **not** proposed: its description is a to-do, and the
Clang comparison has now been run and is reported above.

## Reproducing this triage

```bash
python scripts/triage.py run    --issue 4096
python scripts/triage.py run    --issue 4096 --match match-decl-rejected.json
python scripts/triage.py bisect --issue 4096 --linear
python scripts/triage.py bisect --issue 4096 --linear --match match-decl-rejected.json
cd data/issues/4096 && python measure-history.py > manual-case-release-matrix.txt
cd data/issues/4096 && python probe-clang.py    > manual-case-clang-discriminating.txt
```
