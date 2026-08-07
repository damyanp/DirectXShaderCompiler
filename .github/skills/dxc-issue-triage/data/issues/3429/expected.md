# #3429 — expected symptom

*Written before anything was run.*

Issue: <https://github.com/microsoft/DirectXShaderCompiler/issues/3429> — "DXC Validation
Error: TGSM pointers must originate from an unambiguous TGSM global variable", filed
2021-02-04 against commit `cf044cc96`.

## What is being complained about

**A valid shader is wrongly rejected.** This is *not* a "the diagnostic is unhelpful"
report, although the wording is part of why it looks wrong:

- The HLSL is ordinary: one `groupshared float` array, one `groupshared uint`, a loop that
  indexes the array, all in `cs_6_0`. Nothing in it is ambiguous — there is exactly **one**
  TGSM global that any of these pointers could come from.
- DXC's own front end and optimizer nevertheless emit DXIL that **DXC's own validator
  rejects**. The compile fails; no object is produced.
- The reporter states the failure is optimization-dependent: *"When disabling optimization it
  works, so it seems like some optimization might change the generated DXIL."*

So the symptom is a compile that fails at the DXIL validation stage, with a specific
diagnostic, on input the compiler should accept.

## Reproduces == all of the following

1. `dxc -E main -T cs_6_0 repro.hlsl` (default optimization, i.e. `-O3`) **fails**, and
2. stderr contains `error: validation errors` and at least one
   `error: TGSM pointers must originate from an unambiguous TGSM global variable.`, and
3. the accompanying `note:` blames a `phi` whose type is `float addrspace(3)*` — i.e. the
   rejected value is a merge of TGSM pointers, not a genuinely unresolvable pointer.

The exit status is expected to be **E_FAIL (0x80004005)**. A DXIL validation failure is an
ordinary diagnosed error, **not** an internal failure — nonzero exit here must not be read as
a crash.

## Does NOT reproduce ==

`dxc -E main -T cs_6_0 repro.hlsl` exits 0 and emits DXIL.

## Changed behaviour ==

The compile still fails, but with a different diagnostic (e.g. a front-end error, a different
validation rule, or an internal failure). To keep that distinguishable from a fix, a second
predicate scores "the compile failed at all" independently of the message.

## Expected line/column

The reporter's own 2024 capture reads:

```
newio.txt:9:22: error: TGSM pointers must originate from an unambiguous TGSM global variable.
newio.txt:15:20: error: TGSM pointers must originate from an unambiguous TGSM global variable.
```

`repro.hlsl` is a byte-faithful copy of the comment's code block, **blank lines and trailing
spaces included**, so those line:column pairs should be reproduced verbatim. Do not tidy it;
reflowing it desynchronises every diagnostic already quoted in the thread.

## Repro quality

`complete` — the minimised shader in
[the 2024-04-28 comment](https://github.com/microsoft/DirectXShaderCompiler/issues/3429#issuecomment-2081259226)
was produced by a maintainer (Greg / @pow2clk) from the reporter's private shader, and comes
with the exact command line and its output. The issue *body*'s repro is unavailable (the
reporter could not publish it), but nothing had to be invented here.

## Controls this needs

- **`-Od`** — the reporter's stated workaround. If the predicate fires with `-Od` too, either
  the issue text is stale or the predicate is too loose. Expect `no-match`.
- **A known-good groupshared shader** under the identical profile and flags, to prove the
  predicate does not simply fire on anything using TGSM. Expect `no-match`.

## Hazards noted in advance

- The reported symptom **is a diagnostic**, so the `invalid-probe` classifier's markers and
  the symptom are the same kind of observation. The predicate quotes the diagnostic verbatim
  so the demotion suppression applies.
- The diagnostic's `note:` **echoes the rejected IR back into stderr**. Any absence-style
  predicate over `phi`/`addrspace(3)` would therefore be falsified by the error message
  itself. The predicate here is presence-only, which sidesteps it.
- Release packages ship `dxil.dll` beside `dxc.exe`, so a release probe may be running the
  *signed external* validator while the Debug build runs the internal one. Worth checking
  before attributing any transition to a compiler change.
