# Issue #5587 — Bitfield initialization unclear

## Reported symptom

The reporter has a struct with two bitfield members, an enum-typed 2-bit
field (`field1`) followed by a 30-bit `uint32_t` field (`rest`):

```hlsl
struct SomeBitfield
{
    SomeEnum field1 : 2;
    uint32_t rest : 30;
};
```

`SomeBitfield val = (SomeBitfield)0;` fails to compile:

```
test.hlsl:21:24: error: cannot convert from 'literal int' to 'SomeBitfield'
    SomeBitfield val = (SomeBitfield)0;
```

The reporter says that if the two members are **reordered** (`rest` first,
then `field1`), the same cast-from-`0` initialization "seemingly works and
the generated code looks correct". The reporter's underlying question is
whether `(SomeBitfield)0` is meant to be valid syntax for zero-initializing
a bitfield struct at all, given it depends on member order.

A collaborator (`llvm-beanz`) explains in comments that HLSL treats a
struct initializer/cast as a *vector* initializer (flattening the struct's
scalar members into a vector-like list), which is unusual compared to
C/C++ initialization rules, and that this is suspected to be a bug in how
HLSL's flattened initializers interact with bitfields specifically. No
fix, workaround-only guidance ("initialize each member"), and a
longer-term redesign proposal (C/C++-style initialization,
`hlsl-specs` PR/issue #310) are mentioned. No maintainer states the
order-dependent failure itself was ever fixed; the thread reads as
"known odd/buggy behavior, open design question", not a promised bug fix.

## What "reproduces" means here

There are two distinct, decomposable claims to test against
`-T cs_6_6 -HV 2021`:

1. **Primary defect claim**: with `field1` (enum bitfield) declared
   *before* `rest` (plain bitfield), `(SomeBitfield)0` is rejected with
   `error: cannot convert from 'literal int' to 'SomeBitfield'`.
2. **Order-dependence claim**: with the declaration order reversed
   (`rest` before `field1`), the identical cast-initialization is accepted
   and compiles to (in the reporter's words) code that "looks correct".

"Reproduces" = claim 1 still fails to compile with that same diagnostic
text (or an equivalent conversion-error diagnostic naming `SomeBitfield`),
**and** claim 2 (reordered) still compiles cleanly — i.e. the asymmetry
between the two orderings persists. If claim 1 now compiles (regardless of
what it compiles to), or if the two orderings now behave identically
(both fail or both succeed), the reported inconsistency is gone and the
symptom has changed shape from what was filed.

This is not a crash/assert issue — no `internal_failure` predicate needed.
It is a `regex`/diagnostic-text question, decomposed into two probes
(original order vs. reordered) rather than a single verdict, per the
multi-ask decomposition guidance.

## Repro quality

`complete` — the issue includes the exact file contents and exact command
line (`dxc -T cs_6_6 -HV 2021 -E main test.hlsl`). No reconstruction
needed beyond copying it verbatim.

## Not-compiler-verifiable aspects

None. Both claims (compiles / does not compile, with what diagnostic) are
answerable purely from `dxc` output. The broader design question ("should
HLSL adopt C++ initialization rules") is a language-design decision, not
something a compiler probe can resolve, and the verdict should not attempt
to adjudicate that policy question — only whether the reported compiler
behavior (the order-dependent rejection) still occurs today.
