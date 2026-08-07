# Expected symptom — #3873 "Infinite loop related to struct inheritance and empty struct"

**Reported (2021-07-13):** DXC hangs (does not terminate) compiling a shader where a parent
struct holds a member of an **empty** helper struct, a child derives from it and adds its own
member, and a method on the child calls a method on the helper. The reporter places the hang
in the SROA pass and notes it is related to but not fixed by #3770.

**Repro quality:** `complete` — the reporter supplied a reduced repro and confirmed it against
head `e65a981`.

**What we test:** compile as `ps_6_7`, entry `main`, **with a timeout**.

**Symptom is present if:** compilation does not terminate within the timeout.

**Symptom is absent if:** DXC terminates — whether it compiles, errors or even crashes. A
crash would be a *changed* symptom, not a fixed one, and should be recorded as such.

**This is the first hang in this triage, and the first use of the timeout predicate.** Two
things to be careful about:

1. **A timeout is evidence of a hang, not proof.** A slow-but-terminating compile is a
   different bug. If it times out, re-run with a substantially longer timeout before
   concluding it is infinite — an unbounded loop stays unbounded, a slow one finishes.
2. **A hang cannot be bisected the same way as a crash.** Every probe costs the full timeout
   rather than milliseconds, so the bisection budget is real. Keep the timeout tight enough to
   be affordable but long enough not to produce false hangs on a loaded machine.

**Second reporter:** @simontaylor81 re-reported hitting it independently in 2022-03, "this
time a bit less easy to workaround" — so this is not a single-user curiosity.

**Note:** the shader is valid HLSL. An empty struct member is legal, so the correct behaviour
is to compile it, not to diagnose it.
