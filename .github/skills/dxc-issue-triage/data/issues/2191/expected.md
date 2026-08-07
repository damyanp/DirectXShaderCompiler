# Expected symptom - #2191 Assert when a static const uint is used with [numthreads]

**Repro quality: complete.** The issue body supplies a self-contained three-line shader that
compiles as-is. Only the invocation is unstated, and it is unambiguous: `[numthreads]` plus an
entry point called `main` means `-T cs_6_0 -E main`. `cs_6_0` is deliberately the *oldest*
compute profile, so no release in the bisection range can reject the repro on profile grounds
(SKILL.md step 6, the `invalid-probe` trap).

## What was reported (2019-05-15, @tristanlabelle, collaborator)

Body, in full:

```
Repro:
static const uint eight = 8;
[numthreads(eight, 8, 1)]
void main() {}

Maybe related to #2188
```

The title is the whole symptom statement: **"Assert when a static const uint is used with
[numthreads]"**. No assert message, no stack, no build configuration, no dxc version is given.
Labelled `bug`; milestone `Dormant`; assigned to the reporter; still open.

## What the thread adds

- The only comment (@llvm-beanz, 2024-06-11) just re-links #2188 - no new data in five years.
- #2188 (@xxxbxxx, 2019-05-14, open, `bug` + `fxc-disagrees`) is the *feature* half: FXC accepts
  a `static const` as a `[numthreads]` argument and as an array bound, DXC does not. That issue
  reports a rejection, not a crash.
- #4032 (2021-10-23) reported the same construct and was closed as handled here. Two things in
  it matter and both are pre-run evidence about the symptom:
  - the reporter wrote "**Compiler emits error message and rejects input**" - i.e. by late 2021
    the observed behaviour was a diagnostic, not an assert;
  - @pow2clk's closing comment calls accepting a `static const` here "a new language feature",
    and offers `#define` as the workaround. That is a maintainer position that the *rejection*
    is intended, and that only the *assert* is unambiguously a defect.

So the reported symptom and the still-live complaint are two different things, and they must be
scored separately or the verdict will conflate them.

## The symptom reproduces if

**dxc fails internally** - an assert-enabled Debug build traps (0x80000003), or any build takes
an access violation (0xC0000005), `llvm_unreachable`/`report_fatal_error` (0xE00000002/3), or a
POSIX signal - while compiling the repro. This is `match.json`.

Deliberately *not* keyed to any message text. Per SKILL.md, the same defect wears different
faces across builds: an assert in Debug, an access violation or a bad-cast `E_FAIL` in Release.
No assert string was ever quoted in this issue, so there is nothing to key to even if that were
safe, and the ground truth is a Debug build precisely so an assert can fire at all.

**A well-formed error diagnostic is NOT this symptom.** dxc returns E_FAIL (0x80004005) for
ordinary diagnosed errors on Windows, so a nonzero exit alone must not be read as a crash.

## Secondary claim, scored separately

Whether dxc still *rejects* the construct is a different question from whether it asserts, and
it is what #2188/#4032 are actually about. If the assert is gone but the shader is still
rejected, that is `changed-behavior`, not `does-not-repro`, and the second predicate is what
establishes it. Its exact form is deliberately left until after the primary run, because the
diagnostic text is unknown until observed; it will be added as `match-rejected.json`.

## Controls

- **Negative control** (`variant-literal`): the same shader with `[numthreads(8, 8, 1)]` written
  as literals must compile cleanly and must *not* match either predicate. If it matches, the
  predicate is testing the wrong thing, or the repro's failure has nothing to do with the
  `static const`.
- If dxc asserts on the literal form too, the repro is not isolating what #2191 describes.

## What would make this inconclusive

The report names no build configuration. If the assert is gone from the Debug ground truth *and*
from every release in range, the honest reading is that the crash is unreachable across the
whole checkable window (which starts v1.4.1907, two months *after* this was filed) - not that it
never existed. That must be reported as "never observed in any checkable release", not as
"never happened".
