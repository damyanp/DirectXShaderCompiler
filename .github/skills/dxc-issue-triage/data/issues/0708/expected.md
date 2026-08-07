# Expected symptom — #708 "RegisterOffset is being ignored from RegisterAssignment"

**Reported (2017-10-13):** if the register-assignment-with-offset form is used, e.g.
`... : register(t1[27])`, the offset is ignored.

**Repro quality:** `prose-only` in the issue — no compilable shader was supplied.
The repro here is **agent-constructed** from the description.

**What we test:** declare a resource with `register(t1[27])` and inspect the binding DXC
assigns.

**Symptom is present if:** DXC accepts the declaration and binds the resource at `t1`,
silently discarding the `[27]` offset, with no error or warning.

**Symptom is absent if:** DXC either honours the offset (binding somewhere other than `t1`)
or rejects/diagnoses the syntax.

**Caveat:** the issue never states what the *correct* binding should be, and the
`register(t <n> [<offset>])` form is not documented for SRVs. So "still repros" here means
"the offset is still silently dropped", which is faithful to the report; deciding what DXC
*ought* to do is a human call.
