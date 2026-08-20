# Expected symptom

This is a tech-debt / enhancement request, not a bug report with a shader repro. It asks
that two functions in `lib/HLSL/DxilValidation.cpp`:

- `ValidateDxilOperationCallInProfile`
- `ValidateHandleArgsForInstruction`

each get a `DXASSERT`-style assertion in the `default:` case of the switch statement that
dispatches per-DXIL-opcode validation, so that a DXIL opcode that reaches the function
without a matching `case` fails loudly (in a Debug/assert build) rather than being silently
skipped. The issue explicitly allows the alternative of a comment explaining why the
default case is provably unreachable for a given function, if that can be shown.

"This reproduces" would mean: reading current `main` source, the `default:` case of one or
both of those switch statements is still empty (no assert, no explanatory comment) and no
opcode-completeness check exists elsewhere that would have the same effect. "Does not
reproduce" / fixed would mean an assert (or an equivalent completeness check, e.g. a
static_assert-driven table or a comment justifying the omission) is now present.

This is fundamentally a **source-code-verifiable** question, not a shader-compile
question: there is no HLSL input that "activates" a missing default-case assert in a way a
predicate over `dxc` stdout/exit-code can observe, because the whole point of the request
is to add validation runtime-checking code (a DXASSERT) that isn't there. Wanted: read
both functions' current bodies and check the default case in each. This is expected to be
`not-compiler-verifiable` (a static-analysis/source-reading question) unless the switch's
default branch can be triggered by a real DXIL opcode not covered by any case, which is
also checkable by cross-referencing `DXIL::OpCode` enumerators against the switches'
`case` labels.

Repro quality: **prose-only** (this is a source-level tech-debt request; there is nothing to
compile that would exhibit "an opcode not being validated" as an observable dxc symptom).
