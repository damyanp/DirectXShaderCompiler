# #4415 — expected symptom, written before running anything

**Issue**: [Validator needs to prevent invalid handle in AnnotateHandle](https://github.com/microsoft/DirectXShaderCompiler/issues/4415)
Filed 2022-04-25 by tex3d (a DXC maintainer). Labels: `bug`, `validation`. No comments.

## What the issue says

The body is a single self-contained shader with a `RUN:` line and two prose asks:

```hlsl
// RUN: %dxc -T vs_6_6 -E main %s
struct MyCB {
  uint u;
};
static ConstantBuffer<MyCB> CBV = ResourceDescriptorHeap[CBV.u];

uint main() : OUT {
  return CBV.u;
}
```

> Using CBV.u before defining CBV to a specific resource should result in error. It does result
> in a warning: `warning: variable 'CBV' is uninitialized when used within its own
> initialization [-Wuninitialized]`. Should we make this warning an error by default?
>
> It also looks up the index with an invalid zeroinitializer handle in DXIL, which should cause
> a validation failure in any case:
> `%1 = call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle zeroinitializer, %dx.types.ResourceProperties { i32 13, i32 4 })  ; AnnotateHandle(res,props)  resource: CBuffer`

## Decomposition — this is a two-ask issue

Recording each separately, per SKILL.md ("Decompose multi-ask issues before choosing one
verdict"). The title names only ask B, and `validation` in this repo means DXIL validation
specifically, so **ask B is the headline**.

### Ask A — front end (phrased as an open question, not a demand)

`CBV` used inside its own initializer is diagnosed as a *warning* (`-Wuninitialized`), and the
reporter asks whether it should be an error by default.

- **A reproduces** if today's compiler still only warns: the `-Wuninitialized` warning is
  emitted and the compile **succeeds** (exit 0, DXIL produced).
- **A does not reproduce** if the compiler now errors (or if the warning is gone entirely,
  which would be a different and worse result — record it as `changed-behavior`).

Note this ask is a **question to the project**, not a defect report. Even if it still
reproduces exactly as described, the action on it is a language/product decision, not a fix I
can recommend.

### Ask B — DXIL validator (the title)

DXIL in which `dx.op.annotateHandle` receives an **invalid handle** — `zeroinitializer` in the
reporter's capture, `undef` being the other spelling of the same defect — is accepted by DXIL
validation. The validator should reject it.

- **B reproduces** if a module whose `annotateHandle` takes a `zeroinitializer`/`undef` handle
  **passes** validation (`Validation succeeded.`, exit 0; or `dxc` completes and signs the
  container without a validation error).
- **B does not reproduce** if validation **fails** on such a module. A DXIL validation failure
  exits **E_FAIL 0x80004005** through `dxc` and **1** through `dxv`; per SKILL.md's exit-code
  table **neither is an internal failure**, and must not be scored as a crash.

## The shape of this measurement, and the trap in it

The symptom is an **acceptance**: the validator says nothing. Two consequences:

1. **A clean validator run is vacuous on its own.** `dxv` prints `Validation succeeded.` and
   nothing about what it validated, so that line is equally produced by a module that never
   contained an `annotateHandle` at all, by a module that failed to be read, or by a run that
   never happened. The predicate must therefore score **anti-vacuity self-test lines emitted
   into the same capture**, stating that the module really does call `dx.op.annotateHandle` and
   that its `res` operand really is `zeroinitializer`/`undef`.
2. **The compiler's own output may not exhibit the problem.** The ask is that a validator
   reject input a *third-party producer* could emit. If today's `dxc` no longer emits the
   zeroinitializer handle, ask B is still live and must be measured by **deliberately
   constructing** the invalid DXIL and feeding it to the validator, exactly as a non-DXC
   producer would. Compiler silence on the reporter's shader would then be evidence about the
   front end (ask A), not about the validator.

## What I will run

1. **The `RUN:` line verbatim** — `-T vs_6_6 -E main repro.hlsl` on ground truth `main-debug`
   (1.9.0.5433, `13730886e`). With no output file `dxc` prints the disassembly to stdout, so
   one capture holds the diagnostics, the exit status and the emitted DXIL. This answers ask A
   and shows whether the reporter's `annotateHandle` line is still produced.
2. **A validator harness** (`validate4415.py`, registered as a compiler id so `run`,
   `--expect`, variants and `audit` all apply — SKILL.md, "register the harness as a
   compiler"). It prints self-test lines about the module it is about to validate, then runs
   `dxv.exe`, then reports `VALIDATION-SUCCEEDED` / `VALIDATION-FAILED`, and emits a loud
   `PARSE-WARNING` if the module cannot be read or contains no `dx.op` call.
3. **Deliberately doctored modules**, at minimum:
   - the compiler's own emitted module for the repro, if it contains the invalid handle;
   - a *valid* shader's module with the `annotateHandle` `res` operand rewritten to
     `zeroinitializer`;
   - the same rewritten to `undef`.
4. **Controls**, both directions:
   - *negative*: the unmodified valid module — the predicate must **not** match, proving it
     discriminates on the handle operand rather than firing on everything;
   - *positive / anti-vacuity*: at least one module the validator genuinely **does** reject, so
     that `VALIDATION-SUCCEEDED` is a measurement and not the harness's only possible output.
     Candidates: an `undef` handle on an op that *is* checked (`ValidateHandleArgs` covers
     everything except the four annotate/lib opcodes), and an `annotateHandle` whose *props*
     operand names an invalid resource kind (`InstrOpConstRange`).
5. **History**, bounded by what can actually be probed. `bisect` cannot drive a
   harness-as-compiler (SKILL.md), so release history needs an explicit matrix that holds the
   modules fixed and varies the validator binary — and only releases whose archive ships
   `dxv.exe` can be probed at all. `ResourceDescriptorHeap` requires SM 6.6, so any release
   predating it is an `invalid-probe` for the compiler half.

## Prior expectation from source, recorded before measuring

`lib/DxilValidation/DxilValidation.cpp` `ValidateHandleArgs()` switches `AnnotateHandle`,
`AnnotateNodeHandle`, `AnnotateNodeRecordHandle` and `CreateHandleForLib` to `break` under
`// TODO: add custom validation for these intrinsics`, while every other opcode goes to
`ValidateHandleArgsForInstruction()`, whose comment reads "Make sure none of the handle
arguments are undef / zero-initializer". That check arrived in `9468120e6` (2023-07-21,
PR #5399), i.e. **after** this issue was filed, and excluded `AnnotateHandle` from the start.
So I expect ask B to still reproduce. **This is a prediction, not a result** — it is written
down here so that the measurement can contradict it.

## Repro quality

`complete` — the issue body is a compilable shader plus the exact command line. The doctored
modules and the validator harness are `agent-constructed` additions needed to ask the
validator the question directly; that will be stated wherever they are cited.
