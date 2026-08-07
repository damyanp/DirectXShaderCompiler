# Expected symptom — #1768 "Arrays of structs in GS OutputStreams are not supported"

**Reported (2018-12-12):** a geometry shader whose input/output stream struct contains an
array of structs hits
`DXASSERT(0, "Not support array of struct when split pointers.")` in `SplitPtr`
(`lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp`). The reporter states it looks like it
was never implemented.

**Repro quality:** `complete` — the issue supplies a full geometry shader.

**What we test:** compile the supplied shader as `gs_6_0` with an **assert-enabled Debug**
build (a Release build would not surface the assert).

**Symptom is present if:** compilation fails with an internal compiler error / assert rather
than either succeeding or producing a proper user-facing diagnostic.

**Symptom is absent if:** the shader compiles, or DXC reports a clean diagnostic explaining
that arrays of structs are unsupported in GS streams.

**Note:** an assert-only failure is a `crash`-class bug even when the *feature* is
unimplemented — the correct behaviour for an unimplemented feature is a diagnostic, not an
assert.
