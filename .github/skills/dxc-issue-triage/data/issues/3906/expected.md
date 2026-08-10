# Expected symptom — #3906 "Compiler infinite loop issue"

Written **before** any compiler was run, per step 2.

**Reported (2021-08-13, @hannes-vernooij):** DXC never terminates ("infinite loop") while
compiling a compute shader. The reporter states the hang needs **all three** of:

1. the index used to subscript the unbounded `ByteAddressBuffer` array is returned from a
   **struct member function** (`RenderResourceHandle::readIndex()`);
2. the `ByteAddressBuffer` is **accessed** inside the member function — it need not be used;
3. the member function **returns an array** (tested with `float2`, `float3`, `int2`).

"When any of these steps are missing it will not result in an infinite loop." Workaround given:
wrap the values in a struct and return the struct.

**Repro quality:** `complete` — the full shader is inline in the issue body.

**What is *not* given:** the command line. The only pointer to it was a
`shader-playground.timjones.io` permalink, and that host no longer resolves (DNS failure,
checked 2026-08-10), so the reporter's exact arguments are unrecoverable. The shader declares
`[numthreads(8, 8, 1)] void main(...)` with `SV_DispatchThreadID`, so the stage is compute and
the entry point is `main`. Per the skill's "target the oldest profile that still shows the
symptom", the repro is aimed at `cs_6_0`, the oldest compute profile DXC has, rather than
whatever was current in 2021.

**Language version is an open question, not an assumption.** The report predates HLSL 2021
becoming the default. If today's default rejects the source before codegen, that is an
`invalid-probe`-shaped answer and the repro must be pinned with `-HV 2018`; this will be
measured and recorded, not guessed.

## Symptom present

Compiling the shader above **fails to produce DXIL for a valid shader**, in either of the two
forms one defect of this kind can take:

- the compile **does not terminate** (the reported form); or
- the compile **fails internally** — assert, access violation, stack overflow (`0xC00000FD` is
  the expected shape for runaway recursion), `llvm_unreachable`, `report_fatal_error`.

Both count. #3873 measured exactly this split for another DXC hang: the Release build spun
unboundedly where the clean Debug build tripped an assert on the same input in ~2 seconds, so a
bare `timeout` predicate scored the Debug ground truth `no-repro` and would have reported an
open, always-reproducing bug as fixed. Ground truth here is a Debug build, so the same trap is
live. **Which signatures this defect actually has is to be established by measurement** — the
disjunction is there so that finding either one is scored as a reproduction, not so that one
can be assumed.

## Symptom absent

DXC terminates normally: it either compiles the shader to DXIL (exit 0), or emits an ordinary
diagnosed error (E_FAIL 0x80004005 plus an `error:` line) that is *about the source* rather
than an internal failure. A clean compile is the fix; a diagnosed error would be
`changed-behavior` and would need its own look, since the shader is valid HLSL and the correct
behaviour is to compile it.

## Traps specific to this issue

- **A timeout is evidence of a hang, not proof of an infinite loop.** `triage.py` bounds every
  probe at 60 s. If ground truth times out, re-run once by hand with a far longer bound before
  calling it unbounded — a slow compile finishes, an infinite loop does not.
- **Bisecting a hang is expensive**: every probe that hangs costs the full 60 s wall clock
  rather than milliseconds. Budget for it; prefer binary search unless the history gives a
  reason to scan linearly.
- **The three-condition structure is a ready-made control suite.** The reporter has already
  told us what should *not* hang. Removing exactly one condition at a time gives three
  `--expect no-match` controls, and they are much stronger than a generic "hello world"
  control: they prove the predicate discriminates on the exact axis the report names.
- **Unbounded resource arrays and `space3`** are the sort of thing an old release might not
  accept. Any release that rejects the source is an `invalid-probe`, not a fix.
