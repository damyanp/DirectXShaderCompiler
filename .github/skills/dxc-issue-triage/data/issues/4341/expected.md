# #4341 — [HLSL 2021] Setter array subscript operator overload

Written **before** running any compiler.

## What the issue says

Filed 2022-03-21 by `tomjohnstone`, open, labelled `hlsl-next`. The body is a question:

> How can I implement a _setter_ array subscript operator overload? A getter works like
> this but doesn't require references like C does.

with a `struct MyArray { float4 A[MAX_SIZE]; float4 operator[](int ix) {...} };` snippet
that is a **getter only** — it returns `float4` by value. The body contains no `RUN:` line,
no command line, no compiler output, and no error message. The reporter never states an
observed failure; they state that they cannot express the thing they want.

Thread:

- `natevm` (2022-10-08): "Running into the same issue about a year later. How can we assign
  to the subscript operator?"
- `pow2clk` (2022-11-28): "Unfortunately, this is not currently possible due to lack of
  reference support in HLSL. It is something we want to improve in later versions."
- `llvm-beanz` (2023-06-30): "This is caused by broken behavior in DXC's overload
  resolution. We have a bunch of related issues that will need to be addressed in order to
  support [the const-instance-methods proposal for HLSL 202x]. That feature is effectively
  going to result in us adopting C++ overload rules completely for HLSL."

So there are **two** stated causes in the thread, and they are not the same claim. They must
be measured separately, not collapsed into one verdict.

## Repro quality

`partial` — the struct is quoted verbatim but the *failing* expression (the assignment) is
not written down anywhere in the thread, nor is a profile, entry point or command line. Any
`m[i] = v;` line, the `main()` around it, and the whole command line are **agent-constructed**.
The struct itself is not: `MAX_SIZE 100` / `float4 A[MAX_SIZE]` is quoted from the issue and
is also the exact struct used by
`tools/clang/test/HLSLFileCheck/hlsl/operator_overloading/operator.overloading.implicit-assign1.hlsl`.

## Decomposition — the separate asks

| id | ask | how it is measured |
| --- | --- | --- |
| **A1** | write *through* a by-value `operator[]`: `m[ix] = v;` | compile it and look at the result |
| **A2** | declare a reference-returning `float4 &operator[](int)` — `pow2clk`'s "lack of reference support" | compile the declaration alone |
| **A3** | distinguish a getter from a setter by const-ness of the implicit object parameter (the C++ idiom, and `llvm-beanz`'s "broken overload resolution") | declare both and see which is called / whether it is an error |
| **A4** | is there *any* in-language way to write through a subscript-like member? | a named `Set(int, float4)` method as a control |

## What "this reproduces" means

**A1 is the headline.** The issue reproduces if, on ground truth, there is still **no way to
write through a user-defined `operator[]`**. Three outcomes are possible and they are
different defects, so the repro is built to tell them apart by value, not just by exit code:

The repro seeds `A[0]` with a known value `1.0`, executes `m[0] = 9.0`, and returns `m.A[0]`.

| observed | meaning | verdict |
| --- | --- | --- |
| compile **fails** with a diagnostic naming the assignment | the write is **rejected**. The feature is absent and the compiler says so. `repros` — the reporter still cannot do this | `repros` |
| compiles, `main` returns **1.0** | the write is **silently discarded** — the overload is *not selected* and the store goes nowhere. That is a miscompile, strictly worse than a diagnostic, and would be `changed-behavior` against a thread that only ever claimed the feature was unavailable | `changed-behavior` |
| compiles, `main` returns **9.0** | the write landed; a setter subscript now works and the thread is stale | `does-not-repro` |

"Not selected" vs "rejected" is exactly the distinction the seeded-value design exists to
make; an exit code alone cannot separate the first two rows.

## Predicate plan

Pre-register: the predicate must carry a **positive anchor** as well as whatever clause
captures the symptom, so that a compile which fails for an unrelated reason (wrong profile,
old release that predates HLSL 2021, a typo) cannot satisfy it for free. If the outcome is a
diagnostic, the anchor is the diagnostic text itself quoted verbatim into `match.json` (this
is a diagnostic-quality issue, so the `invalid-probe` markers and the symptom are the same
kind of observation — see SKILL.md on #3055). If the outcome is a value, the anchor is the
DXIL that only a successful codegen can emit.

## `-HV 2021` — to be measured, not assumed

The title says `[HLSL 2021]` and operator overloading on user-defined structs is an HLSL 2021
feature, so `-HV 2021` is *plausibly* load-bearing here — but plausible is not measured, and
an inherited `-HV 2021` has manufactured a false feature floor before. Two things get
measured explicitly and written down:

1. **On ground truth**, compile the repro with and without `-HV 2021` and compare. `main`'s
   default is already 2021, so the flag should be inert there; if it is not, that is itself a
   finding.
2. **On a release that accepts `-HV 2021`**, compile with and without it. If dropping the
   flag changes the result (e.g. `operator[]` overloading stops being recognised), the flag
   is genuinely load-bearing and the pre-2021 releases are honest `invalid-probe`s. If it
   does not change the result, the flag must be dropped from `cmd.txt` to widen the history.

Releases that answer `dxc failed : Unknown HLSL version: 2021` and exit `0x1` are
**invalid probes**, not clean runs. Confirm the classifier demotes them rather than counting
them as "fixed".

## Prediction of the history

Not predicted. If A1 turns out to be a diagnostic that has been emitted since HLSL 2021
shipped, the honest history is `always-repro'd` **over the releases that can express the
feature at all**, with the count of demoted older releases stated.

## Expected suggested action, if A1 confirms

This is a language-feature request that a maintainer has already answered twice in the
thread, with a named successor design (`hlsl-specs` proposal 0007). The likely action is
`enhancement-not-bug` / `still-valid-keep-open` rather than anything closable. The verdict
follows the evidence, not this paragraph.
