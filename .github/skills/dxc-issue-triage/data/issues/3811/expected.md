# Expected symptom — #3811 "Reading uninitialized value in dynamic loop produces undef with no error/warning"

Written **before** any compiler was run, from the issue text alone (filed 2021-06-02,
label `validation`, **0 comments** — there is no maintainer position to weigh).

## What was reported

A helper takes `out float result` and accumulates into it without ever initialising it:

```hlsl
void Accumulate(int count, out float result)
{
    // result += values[0];  // <-- This will fail validation and produce an error message
    for (int i = 0; i < count; i++)
        result += values[i];  // <-- This will not
}
```

`out` parameters are **not** copied in, so `float result = 0.0;` in `main` does not initialise
the callee's `result`. The read is genuinely uninitialised in both spellings.

Command as filed: `dxc.exe -T vs_6_0 source.hlsl` — default optimisation, no `-E` (defaults to
`main`), no `-Fo` (so dxc disassembles to stdout).

The reporter pasted the DXIL they got. The three lines that carry the claim:

```
  %7  = phi float [ %10, %5 ], [ undef, %4 ]     ; loop-carried accumulator seeded with undef
  %10 = fadd fast float %9, %7                   ; the undef reaches arithmetic
  %15 = phi float [ undef, %0 ], [ %10, %13 ]    ; and the count<=0 path merges undef out
```

Their hypothesis: it escapes diagnosis "because undef is permitted in phi nodes".

## The two claims, tested separately

**(a) Loop version** — compiles with **no error and no warning**, and the emitted DXIL seeds
the loop-carried accumulator with `undef`.

**(b) Straight-line version** (the commented-out line, loop removed) — **does** produce an
error and fails validation.

(b) is the reporter's own control and is what makes the report meaningful: the complaint is
not "undef exists" but that **the same defect is diagnosed one way and silent the other**. If
(b) no longer errors, the issue's framing has changed and that is the headline, not a footnote.

## Symptom is PRESENT if

Compiling `repro.hlsl` exactly as filed:

1. emits **no `error:` and no `warning:`** (exit 0), **and**
2. the DXIL contains a `phi float` whose incoming value is `undef` — i.e. the uninitialised
   accumulator survives into the module.

Both halves are required. Clause 2 is a *positive* clause and is therefore the anchor: a
compile that never produced DXIL cannot satisfy it, which is what stops clause 1 (an absence
clause) from being satisfied for free by a failed parse.

## Symptom is ABSENT if

- dxc emits any diagnostic about the uninitialised read (front-end warning/error), **or**
- DXIL validation rejects the module, **or**
- the accumulator is no longer seeded with `undef` (e.g. it is zero-initialised).

## Predicate traps anticipated for this issue

- **`undef` appears in correct DXIL.** `loadInput`'s trailing `gsVertexAxis` operand is `undef`
  in every non-GS shader — it is right there in the reporter's own paste
  (`@dx.op.loadInput.i32(i32 4, i32 0, i32 0, i8 0, i32 undef)`). A predicate matching `undef`
  anywhere would fire on every clean vertex shader. The predicate must name *this* undef.
- **The symptom is partly an absence.** Any release that fails to parse the shader also emits
  no warning. Guarded by the positive anchor above; probes must be checked for
  `invalid-probe`, and a probe only counts if that release actually compiled the repro.
- **This is not a crash.** E_FAIL (0x80004005) here would be an ordinary diagnosed error.
- **The undef is in an LLVM `fadd`, not a `dx.op`.** A predicate keyed to `dx.op.*` arithmetic
  would miss it entirely.

## Also to be determined (not part of the predicate)

- **Optimisation dependence.** At `-Od` the accumulator is an `alloca`, so a literal `undef`
  phi may not appear at all. An undef that only survives at one optimisation level is a
  materially different report; test `-Od` and say which levels show what.
- **Where the diagnosis in (b) comes from** — DXIL validator rule, a Sema check, or an
  optimisation artefact. This decides whether `validation` is the right label.
- **`: OUT` is an arbitrary (non-system) output semantic**, which is allowed to be partially
  undefined. That weakens "the output is garbage" as a complaint but not the reporter's actual
  complaint, which is the inconsistency between (a) and (b). Note it; do not let it decide the
  verdict.

## Repro quality

`complete` — a full, self-contained shader, the exact command line, the reporter's own DXIL,
and an in-source control (the commented-out line). Nothing had to be invented.

## Controls planned

| shader | role | expectation |
| --- | --- | --- |
| `variant-straightline` | claim (b): the input dxc **does** diagnose — proves the check exists and the pipeline reaches it | `no-match` |
| `control-initialized.hlsl` | the same loop with `result = 0;` added — correct code, one line different | `no-match` |
| `-Od` run of `repro.hlsl` | optimisation dependence | recorded, judged after |
