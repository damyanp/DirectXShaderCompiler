# Expected symptom - #3150 Unspecified behavior from new-to-DXIL sdiv instruction

**Repro quality: prose-only, and deliberately so.** There is no bug to reproduce. This is a
specification / documentation issue: DXIL inherited LLVM's `sdiv`/`udiv` without stating what
happens for division by zero or for `INT_MIN / -1`.

**This issue is ACTIVE.** 14 comments, most recent 2026-01-22. Triage must not talk over a live
design discussion; the job here is to check the concrete, checkable claims, not to opine on the
design.

## What "reproduces" cannot mean here

Nothing. Every compiler involved is behaving as designed; the complaint is that the design is
unwritten. Forcing a `repros` / `does-not-repro` verdict would be a category error. Expected
verdict class: `not-compiler-verifiable` (the observable part is driver behaviour) with the
actionable part being a documentation gap.

## Concrete, checkable claims

1. **@damyanp, 2024-07-03: "Plan: add a note in DXIL.rst that sdiv divide by zero behavior is
   undefined."** Did that note land? Check current `docs/DXIL.rst`.
2. **What does DXC emit today** for integer division - the LLVM `sdiv`/`udiv` instructions, or
   the DXIL `UDiv` operation? The thread turns on this distinction.
3. **Does DXC's own validator take a position?** `INSTR.NOIDIVBYZERO` / `INSTR.NOUDIVBYZERO`
   exist in the rule table. If they fire, then "undefined" is not the whole story, and no
   comment in the thread mentions them.

## Out of scope

Which of the four options in the thread is right, and what drivers do. @llvm-beanz has already
measured real drivers; repeating that needs a GPU and is not attempted.
