# #3055 — notes

**Status: `repros`.** Still reproduces on `main` and on every release binary that exists.

Ground truth: `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`,
Debug build, verified with `dxc --version` before any probe was run.

## The repro

`repro.hlsl` is the issue body verbatim; `cmd.txt` is `-T ps_6_0 -E main repro.hlsl`. Nothing
had to be invented — the profile is implied unambiguously by `float4 main(...) : SV_Target`,
and `ps_6_0` is also the oldest profile that shows the symptom, which is what keeps the
release probes valid (SKILL.md step 6). Repro quality `complete`.

**The issue body was edited on 2023-09-27.** `llvm-beanz` reported on 2023-07-14 that the
example then in the body compiled cleanly; `pow2clk` answered that the underlying issue
persists and replaced the example ("Exampled updated to a quite plausible mistake to make").
The 2020 example is not recoverable from the issue text and was not triaged. Everything below
is about the current body.

This matters for anyone spot-checking the thread: read top-down, a maintainer says "compiles
successfully now" three comments above a body that does not compile. `text_stale` is *not*
set, because the title and body do describe what the compiler does — accurately, down to the
quoted output. It is the *comment* that has gone stale. See `method-notes.md`.

## Ground truth

`out-main-debug.txt`, exit `0x80004005` (E_FAIL — an ordinary diagnosed error, not a crash):

```
repro.hlsl:5:14: error: no matching member function for call to 'Sample'
  return tex.Sample(samp, coord);
         ~~~~^~~~~~
repro.hlsl:5:14: note: candidate function template not viable: requires 3 arguments, but 2 were provided
repro.hlsl:5:14: note: candidate function template not viable: requires 4 arguments, but 2 were provided
repro.hlsl:5:14: note: candidate function template not viable: requires 5 arguments, but 2 were provided
```

Character-for-character the output quoted in the issue, modulo `<source>` → `repro.hlsl`.

## Predicate and controls

`match.json` is an `all_of` of three clauses: the error is emitted, the notes are about
*arity*, and nothing anywhere names the `SamplerComparisonState` → `SamplerState` conversion.
Clause 3 is the defect; clauses 1 and 2 exist because a bare absence clause is satisfied for
free by a compile that never reached overload resolution.

Deliberately **not** used: `nonzero_exit`. Both the repro and a correct rejection exit
`0x80004005`, so exit status carries no information on a diagnostic issue (SKILL.md step 4).
Also not used: `internal_failure` — nothing here crashes.

Two controls, both captured, both `--expect no-match`, both pass:

| control | what it is | why |
| --- | --- | --- |
| `variant-control-correct-sampler-main-debug.txt` | same shader, `SamplerState samp` | known-good input; compiles clean and emits DXIL |
| `variant-control-arity-main-debug.txt` | `tex.Sample(samp)`, **correct** sampler type | fails overload resolution for a reason dxc states correctly and completely |

The second is the load-bearing one: it satisfies clauses 1 and 3 and is rejected only by
clause 2. Without clause 2 the predicate would score *correct* diagnostic behaviour as the
bug.

It is also evidence in its own right. With the correct type and one argument, dxc lists
**four** candidates — requires 2, 3, 4, 5 arguments. With the wrong type and two arguments it
lists **three** — 3, 4, 5. The candidate that disappears is the 2-argument overload, which is
exactly the one the user meant. The intended candidate is the only one suppressed.

## History — `always-repro'd`, v1.4.1907 … v1.9.2607

`bisect` short-circuited after two endpoints, so a **`--linear` scan of all 20 releases** was
run as well. Every one reproduces; there is no transition and no window. The issue history
mentions a behaviour change, which is precisely when SKILL.md requires `--linear`, and here it
was doubly warranted because the change was to a *different* example.

Spot-checking `out-v1.4.1907.txt` (2019-07) against `out-main-debug.txt` (2026): the
diagnostic is **byte-identical**, including the caret art. Nothing about this message has
moved in seven years.

Zero probes were classified `invalid-probe`; `bisect` skipped nothing. See `method-notes.md`
for why that is not luck-free.

v1.4.1907 is the bisection floor, so "always" means "for as long as it is possible to check",
not "since the issue was filed" — though here the two nearly coincide, the issue being from
2020.

## Not specific to `Sample`

`variant-gatherred.hlsl` makes the same mistake on `Texture2D::GatherRed`
(`match-gatherred.json`, `--expect match`, passes). Identical shape: the error, then notes
requiring 3, 4, 6 and 7 arguments, and nothing about the sampler type. So this is the
intrinsic-method overload path, not one intrinsic — which is what the issue title claims and
what `pow2clk` meant by "the underlying issue still likely exists".

## Mechanism, from source

The output observation is corroborated by the code, which is stronger evidence. Read-only; no
DXC source was modified.

1. `HLSLExternalSource::DeduceTemplateArgumentsForHLSL`
   (`tools/clang/lib/Sema/SemaHLSL.cpp:11356`) selects intrinsic-method candidates with
   `FindIntrinsicByNameAndArgCount(...)` — **by argument count first** — then calls
   `MatchArguments`.
2. `MatchArguments` computes `badArgIdx`, documented at `SemaHLSL.cpp:5396` as "The first
   argument to mismatch if any". On failure the caller does `++cursor; continue;`
   (`SemaHLSL.cpp:11364-11369`) and **the value is discarded**. The compiler works out which
   argument is wrong and throws the answer away.
3. Exhausting the candidates returns a bare
   `Sema::TemplateDeductionResult::TDK_NonDeducedMismatch` (`SemaHLSL.cpp:11456`), carrying no
   `FirstArg` / `SecondArg`.
4. `DiagnoseBadDeduction` (`tools/clang/lib/Sema/SemaOverload.cpp:9330`) then hits an explicit
   HLSL-specific early return at lines 9355-9360:

   ```cpp
   // HLSL Change Starts
   // The implementation for template argument deducation does not yet provide
   // FirstArg and SecondArg information for failure cases; ellide the note in
   // this case.
   if (FirstTA.isNull() || SecondTA.isNull()) return;
   // HLSL Change Ends
   ```

That comment *is* the issue: "elided due to incomplete error reporting from the HLSL code".
The remaining notes come from candidates rejected on arity before deduction, which is why the
user is told only about overloads they were not calling.

## Comparison compilers

Both were controlled with the known-good shader before being believed
(`manual-case-compiler-explorer.txt`).

- **FXC** (`fxc_10_0_19041`) lists the candidate signatures, each showing `SamplerState` as
  the first parameter: `error X3013: 'Sample': no matching 2 parameter intrinsic method` /
  `Possible intrinsic methods are: Texture2D<float4>.Sample(SamplerState, float2|…)`. A real
  FXC/DXC diagnostic-quality difference — hence the `fxc-disagrees` proposal.
- **Clang** (`hlsl_clang_trunk`) already emits the wanted note:
  `note: candidate function not viable: no known conversion from 'SamplerComparisonState' to
  'hlsl::SamplerState' for 1st argument`.

  The Clang pane needs its control, because Clang's DXIL backend cannot lower a pixel shader.
  It has one: on `control-correct-sampler.hlsl` Clang gets past Sema and fails later with
  `Unsupported intrinsic llvm.dx.store.output.v4f32 for DXIL lowering` and no overload error
  at all. The repro fails in Sema and never reaches lowering, so the pane is sound.

Compiler Explorer: <https://godbolt.org/z/M7e5Yrr36> — four panes, banner from
`godbolt-note.txt`, every pane's output verified against what the banner claims. CE runs
Release builds and `dxc_trunk` is a rolling build, so it corroborates the local Debug ground
truth rather than overruling it. `dxc_1_6_2112` and `dxc_trunk` agree exactly, which is CE's
whole DXC range showing no movement.

## Labels

Now: `tech-debt`, `diagnostic`. Both correct; no removals.

Proposed adds:

- **`fxc-disagrees`** — "Issues tracking differences between FXC and DXC". Measured, not
  assumed: FXC names the parameter type, DXC does not.
- **`usability`** — "Issues impacting usability". The input is a plausible slip and the
  message actively misdirects, listing only overloads the user did not call.

Considered and **rejected**: `check-in-clang`, whose description is "See if this repros in
clang as well" — an instruction to perform a check that this triage has already performed and
recorded. Adding it would ask for work already done. The Clang result is in the draft comment
instead. Also rejected: `incorrect-code`, whose name ("DXC emits wrong code") and description
("handling of incorrect code") point opposite ways; a label that could be read either way is
worse than no label.

## Assessment

The defect is real, unchanged since at least 2019, reproduces on every compiler that can be
tested, is confirmed in the source, and generalises across intrinsic methods. It is also
already acknowledged by a maintainer, who decided in 2023 to keep it open. Re-confirming it
adds little on its own, so the useful parts of this triage are the three things the thread
does not yet contain: the exact elision point in source, the fact that the *intended* overload
is the one candidate suppressed, and that Clang's HLSL front end already produces the desired
note — which turns "how should this be fixed" into "there is a reference implementation".

Suggested action `still-valid-keep-open`; confidence high.
