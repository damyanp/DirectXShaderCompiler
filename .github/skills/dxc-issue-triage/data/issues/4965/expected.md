# Expected symptom — #4965

Repro quality: **complete**. The issue body gives the exact HLSL source and the exact
command line (`/T ps_6_2 /E f`); nothing needs to be reconstructed.

## Source (as filed)

```c
int f( int)
{
    return 0 ;
}

int a;
static int b = f ( a) ;
```

`f`, the function used as the pixel-shader entry point (`-E f`), is also called at global
scope to initialize `static int b`. `f` takes an `int` parameter and has no `SV_*` semantics
— this is not a shape a real shader would use; the reporter later confirms as much
("It is not for a valid use case. It's an attack.") and a maintainer agrees it is invalid
input DXC should diagnose rather than crash on ("It is invalid shader code that we don't
produce a good error for.").

## Reported symptom

Compiling that source with `-T ps_6_2 -E f` is reported to fail **internally**, not with an
ordinary diagnosed error. The issue body says the standalone `dxc.exe` shows, "randomly" (its
word) one of two things:

- `Internal compiler error: access violation. Attempted to read from address 0x0000000000000018`
- `error: llvm::cast<X>() argument of incompatible type!`

A maintainer comment (Keenuts, 2023-01-26) reproduces at head-of-the-time
(`ce9b3a2c8b56d9e24b5f3cdfa24c8c938eafb56e`) with a **third** shape — a Debug-build assert:

```
otherwise we flattened a library function.dxc: lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp:6093:
void (anonymous namespace)::SROA_Parameter_HLSL::replaceCall(llvm::Function *, llvm::Function *):
Assertion `false && "otherwise we flattened a library function."' failed.
Aborted
```

A later maintainer comment (Keenuts, 2023-02-01) reports that on Linux, with asserts disabled,
the same repro instead makes "an invalid pointer load in `GlobalIsNeeded`" and segfaults —
i.e. the *same* defect (a null/garbage global reached where a non-null one is assumed),
manifesting differently depending on build configuration (Debug assert vs. Release
access-violation vs. Linux SIGSEGV), which matches the "one defect, several signatures" pattern
in the triage method (`internal_failure` composed with `any_of` across exit codes).

Nobody in the thread claims this was ever fixed; the discussion is entirely about whether
catching the fault via SEH (Windows) is "controlled termination" (llvm-beanz's position) versus
whether the crash itself, or the underlying invalid-input handling, should be fixed at all
(open question, not resolved in-thread). llvm-beanz explicitly separates two concerns: (1) the
process does not have an *uncontrolled* crash today because SEH catches the access violation
in the Windows CLI driver (`dxc.cpp` traps it and reports `Internal compiler error: ...`), and
(2) the underlying invalid input is not diagnosed and instead reaches an internal fault — that
second half is the open defect.

## What "this reproduces" means here

The compiler exits via one of DXC's own internal-failure paths for this source/args
combination — an assert trap (Debug: `0x80000003`/`0xE0000001`), an access violation
(`0xC0000005`), or another internal-error HRESULT/marker from the same defect family — rather
than exiting 0 or producing an ordinary `error:`-only diagnostic (E_FAIL) that never reaches
an internal-error path. Because this is a crash-shaped issue, the predicate is
`internal_failure` (per the skill's "use this for all crash/assert issues" rule), not a text
match on any one of the three quoted messages — the messages differ across builds by design.

`expected.md` is write-once past the first probe; anything found to differ goes in `notes.md`,
not here.
