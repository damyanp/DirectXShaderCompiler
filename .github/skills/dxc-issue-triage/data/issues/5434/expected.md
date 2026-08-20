## Issue 5434 — expected symptom

Filed 2023-07-18 as an **enhancement** request (labels: `enhancement`, `tech-debt`,
`validation`), not a bug report with a repro. The body asks for two things:

1. `DxilValidation.cpp` should validate `Annotate*Handle` intrinsics "deeper than just
   validating that the handle arguments are valid" — i.e. beyond whatever baseline
   handle-argument check already exists.
2. Specifically: check that the handle actually **originated from a valid source** — a
   `Create*Handle` call, or "an external constant" — rather than accepting any handle
   value.

"This reproduces" (i.e. the gap the issue describes still exists) means: a call to
`AnnotateHandle`, `AnnotateNodeHandle` or `AnnotateNodeRecordHandle` whose handle operand
provably did **not** come from any `Create*Handle`/`Allocate*OutputRecords` call — the
simplest and cheapest case being a bare `zeroinitializer` or `undef` handle value, the
same malformed input `#5399` (commit 9468120e6, 2023-07-21) made every *other*
handle-consuming DXIL op reject — passes DXIL validation without a diagnostic.

"Fixed" would mean the validator now emits an error for that case (or a documented
superset of it) for the three `Annotate*` opcodes, matching the behaviour every other
handle-consuming opcode already has.

There is no reporter-supplied HLSL repro to reuse; per `DxilValidation.cpp` itself
(`ValidateHandleArgs`), `AnnotateHandle`, `AnnotateNodeHandle`, `AnnotateNodeRecordHandle`
and `CreateHandleForLib` are the **only** four opcodes that skip
`ValidateHandleArgsForInstruction` entirely, next to a comment:
`// TODO: add custom validation for these intrinsics`. A normal HLSL shader compiled by
dxc's front end never produces a mismatched handle — CodeGen always emits a matching
Create+Annotate pair — so the only way to exercise the gap is to hand-construct DXIL
that violates the invariant and feed it to the validator directly. Repro quality:
**agent-constructed** (hand-written `.ll`, no reporter shader to adapt).

`CreateHandleForLib`'s "handle" argument is a resource-struct pointer, not one of the
three handle types `ValidateHandleArgsForInstruction` checks, so it is excluded from this
probe; the finding here is scoped to the three `Annotate*Handle` opcodes the issue title
names.
