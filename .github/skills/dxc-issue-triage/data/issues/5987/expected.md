# Expected symptom (written before running anything)

Issue: https://github.com/microsoft/DirectXShaderCompiler/issues/5987
"Error assigning struct into amplification payload"

## Reported repro

An amplification shader (`as_6_7`) that:
- declares a struct `s` containing a `float4x4`, an `int[3]`, and a `float2`,
- wraps it in `payloadType { s data; }`,
- declares `groupshared payloadType payload;`,
- assigns a whole-struct value into `payload.data` (`payload.data = blah;`) before
  calling `DispatchMesh`.

Reporter's exact command: `dxc amplification.hlsl -T as_6_7`.

## Reported behaviour

Compiling emits:

```
error: llvm::cast<X>() argument of incompatible type!
```

The reporter says commenting out `payload.data = blah;` makes the error go away, and that
"unwrapping" the struct so all members of `payloadType` are loose (not nested inside `s`)
also avoids it — so the trigger is a whole-struct assignment into a member of the
groupshared payload, not merely the payload's existence.

The reporter also notes that on a *Debug* build of dxc this hits "the same assert" as
issue #5338, but says the two repros are different (5338 has an explicit cast; this one has
no cast, `blah` is just a `(s)0`-initialized struct being assigned whole). Per this skill's
own single-writer/parallel-worker rules, that similarity is a hypothesis for collation to
check across issues, not something to assert here — this file records only what #5987 itself
claims and what is measured against #5987's own repro.

The one comment on the issue (damyanp, 2024-10-28) is only a Compiler Explorer link
(https://godbolt.org/z/a1vsvfhPz), no verdict text — must inspect it directly, do not assume
from the presence of the link alone whether it shows the bug fixed or still occurring.

## What "reproduces" means here

- On the ground-truth Debug build (`main-debug`): an internal failure — an assert trap
  (`0x80000003`) or a C++-exception-style assert (`0xE0000001`), per the `internal_failure`
  exit-code table in this skill, since the reporter says Debug hits an assert.
- On a Release-style build (no asserts compiled in): the reported diagnostic text
  `llvm::cast<X>() argument of incompatible type!` at exit E_FAIL (0x80004005) — the one
  internal-failure shape the exit code alone cannot distinguish from an ordinary diagnosed
  error, per this skill's exit-code table, so the text marker is required in the predicate too.
- A clean, error-free compile of the exact repro (with the whole-struct assignment present)
  is "does not reproduce".
- Commenting out `payload.data = blah;`, or unwrapping `payloadType` so its members are not a
  nested struct, are the reporter's own *negative controls* (no error) — useful for a control
  probe, not part of the primary repro.

Repro quality: **complete** — the reporter's own repro is copied verbatim above with no
reconstruction needed.
