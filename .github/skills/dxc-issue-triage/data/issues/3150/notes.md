# #3150 Unspecified behavior from new-to-DXIL sdiv instruction

**Verdict: not-compiler-verifiable.** Nothing to reproduce - this is a specification and
documentation gap, and the thread is an **active design discussion** (14 comments, most
recent 2026-01-22). Triage should not talk over it; below are only the checkable facts.

## 1. The planned documentation change never landed

@damyanp, 2024-07-03: *"Plan: add a note in DXIL.rst that sdiv divide by zero behavior is
undefined."*

Current `docs/DXIL.rst` documents divide-by-zero **only** for the DXIL `UDiv` *operation*:

> Divide by zero returns 0xffffffff for both quotient and remainder.

There is no statement anywhere about the LLVM `sdiv`/`udiv` *instructions*, which is the
distinction the whole thread turns on. The `docs` label is correct and the action is still open.

## 2. DXC emits the LLVM instructions, not the DXIL operation

```
%7  = sdiv i32 %5, %6
%11 = udiv i32 %9, %10
```

Confirms @llvm-beanz's 2025-01-08 summary.

## 3. A detail not raised in the thread: the validator's div-by-zero rules are unreachable

`INSTR.NOIDIVBYZERO` / `INSTR.NOUDIVBYZERO` exist and are enforced in
`lib/DxilValidation/DxilValidation.cpp` (~L3592-3610) - but only for a **literal constant
zero** denominator.

DXC can never emit that. The constant folder rewrites `a / 0` to `undef` before validation
runs, so the diagnostic is a different one:

```
error: Assignment of undefined values to UAV.
```

This still holds with `-Od`. So those two validation rules are effectively dead for
DXC-produced DXIL and can only fire on DXIL from other producers (dxilconv, external tools).
Anyone reasoning about "does DXIL already take a position on division by zero?" should know
the rules exist but are unreachable through this front end.

## Assessment

Leave to the active discussion. Not a triage verdict; the useful contributions are the three
facts above, and only #1 and #3 are likely new to the participants.
