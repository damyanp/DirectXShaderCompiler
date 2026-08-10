# #4350 — expected symptom (written before running any compiler)

**Issue**: "Internal Compiler error: calling method that modifies const object",
filed 2022-03-25 by tex3d. Labels: `bug`, `hlsl-next`. Body says "Related to #4340."

## What the reporter says happens

The body is a test-shaped snippet with its own RUN line:

```
// RUN: %dxc -T vs_6_0 %s | FileCheck %s
// Internal Compiler error: llvm::cast<X>() argument of incompatible type!
```

A file-scope (therefore implicitly const / `$Globals`-backed) struct object `Obj` has a
non-`const` member function `Set()` that writes a member. Calling `Obj.Set()` makes dxc fail
**internally** rather than diagnose the const violation.

Three maintainer comments (llvm-beanz, 2024-07-24) add: a Compiler Explorer link
(`https://godbolt.org/z/adMedG6xc`, a `cs_6_6` restating of the same shader), the statement
that "This requires a language change to get right because HLSL's overload resolution doesn't
handle const-ness of the implicit object", and a link to the hlsl-specs proposal
`0007-const-instance-methods.md`. So the *desired end state* is a language change; the
*reported defect* is that the compiler crashes instead of diagnosing.

## "This reproduces" means

dxc fails **internally** on the repro — an internal failure in the sense of `is_internal_failure`,
not merely a nonzero exit. Concretely, any of:

- exit `0x80004005` (E_FAIL) **whose output carries the `llvm::cast<X>() argument of
  incompatible type!` text** — this is the exact face the reporter saw, and per the skill's
  exit-code table it is the one internal failure the status code alone cannot distinguish
  from a syntax error;
- a Debug assert: exit `0x80000003` (trapped `DXASSERT`) or `0xE0000001` (C++-exception assert);
- an access violation `0xC0000005`, `llvm_unreachable` `0xE0000002`, `report_fatal_error`
  `0xE0000003`, or any other `0xC`/`0xE` structured exception;
- `0x80AA0018` / `0x80AA001B`-`1D` (DXC internal / LLVM fatal / cast HRESULT);
- on a Linux build (Compiler Explorer): signal exit 139/134.

**Assume this defect has more than one face until measured.** A Debug build with asserts
enabled may trap an assert *before* reaching the bad `llvm::cast`, so the ground-truth build's
signature may differ from the reporter's Release-build one, and old releases may crash with
completely empty stderr. The predicate is therefore `internal_failure`, which is defined on
exit status first and text second — **not** a `contains "llvm::cast"` match. Matching the
message text is the documented single biggest source of wrong verdicts in this workflow.

## "This does NOT reproduce" means

dxc either compiles the shader successfully (exit 0), **or** rejects it with an ordinary
diagnosed error: exit `0x80004005` (E_FAIL) with an `error:` line and **no** internal-failure
marker. A clean `error: cannot modify a const object` / `'this' argument has type 'const ...'`
diagnostic would be a *fix* of the reported defect (the crash), even though the language
question in llvm-beanz's comment would remain open. If that is what happens, the status is
`does-not-repro` for the crash, and the issue is still live as an `hlsl-next` language item —
that distinction must be stated plainly rather than collapsed into "fixed".

E_FAIL alone is NOT a crash. 0x80004005 is dxc's status for a plain syntax error, an invalid
target profile and a DXIL validation failure.

## "Changed behavior" would mean

Still failing internally, but with a different signature than reported (e.g. a Debug assert
rather than the bad cast), or still crashing under a different spelling of the repro.

## Repro quality

`complete` — the body carries a self-contained shader and the exact command line
(`-T vs_6_0`). No entry point is named; `main` is dxc's default, and the shader defines `main`.

## Hazards specific to this issue, to check before believing any result

1. **Multiple faces of one defect.** Score with `internal_failure`, never message text.
2. **Language-version default drift.** The repro is from 2022 and names no `-HV`. Today's
   default is HLSL 2021; older releases defaulted to 2016/2018. If the crash is HV-dependent,
   a release boundary could be an artifact of the default moving, not of a fix. Measure
   `-HV 2018` and `-HV 2021` explicitly as labelled variants before dating anything.
3. **Const-ness of a file-scope object is the whole point.** A control where `Obj` is `static`
   (mutable, not `$Globals`-backed) should compile cleanly — that is the negative control that
   proves the predicate is not firing on everything.
4. **`invalid-probe` across releases.** Member functions on structs are old, so feature
   absence is unlikely, but a release that rejects the input for an unrelated reason (unknown
   HLSL version, profile) must not be read as "clean". Run a feature-presence control.
5. **A crashed probe measured nothing** — except here, where the crash *is* the symptom, so
   `invalid-probe` demotion of a matching probe must not fire.

## Prediction (recorded so it can be falsified)

Not recorded as a prediction. The evidence decides. The two live possibilities are (a) it
still fails internally on `main`, and (b) `main` now emits an ordinary diagnostic and the
crash is gone while the language issue remains open. Both are consistent with the thread.
