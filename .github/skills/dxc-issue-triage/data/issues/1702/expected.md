# Expected symptom — #1702 "Array as parameter of function"

**Reported (2018-11-13):** for a function parameter declared as an unsized array
(`float4 Func(float4 a[])`), FXC reports `error X3072: 'a': array dimensions of function
parameters must be explicit`, while DXC "does naught — no error no output, no code
production". A maintainer comment the same day showed DXC was in fact **asserting** in
`SROA_Helper::RewriteBitCast`. In 2024-05 `llvm-beanz` confirmed it still reproduced and
linked a godbolt.

**Repro quality:** `complete` — the issue supplies a full pixel shader.

**What we test:** compile the supplied shader as `ps_6_0`.

**This issue has two distinct symptoms over time**, so it is tracked with two predicates:

- `match.json` — **issue-as-filed symptom**: DXC emits *no diagnostic at all*. Present when
  the output contains no "error". Note a crash prints "Internal compiler error", so this
  predicate is false during the crashing era; bisecting it therefore dates the point where
  the crash was replaced by silent acceptance.
- `match-crash.json` — **2018 symptom**: the assert/internal compiler error.

**Symptom is absent if:** DXC emits a proper X3072-equivalent diagnostic.

**Note:** the maintainer view (2024) is that this needs larger parameter-passing work and
will likely be addressed in Clang rather than DXC; DXC draft PR #5249 was not expected to
land.
