# Issue 4648 — expected symptom

*Written before running any compiler, from the issue text only (filed 2022-09-14, still open).*

## What the issue says

Body, in full:

> `unsigned int16_t g;`
>
> result
>
> > Internal compiler error: access violation. Attempted to read from address 0x0000000000000008
>
> Qualifiers (static, extern...) don't change the observable behavior.
> *Fun fact: use a matrix/vector expansion (`uint16_t1x1`) and it doesn't crash anymore*

Title: `unsigned int{16,32,64}_t at global scope causes Segfault (attempted to read from 0x8)`

Comments:

1. **pow2clk** (2022-09-19, collaborator): the supported spelling is `uint16_t`, "which worked
   when I tried it"; the crash is nevertheless a bug.
2. **siliconvoodoo** (2022-09-20, reporter): not blocking.
3. **llvm-beanz** (2023-11-16, collaborator): "I ran across this issue myself recently. There's
   something gnarly about how 16-bit type aliases are handled" + a Compiler Explorer link.
4. **damyanp** (2024-09-30, member): "This should be reported as an error - not crash, but we
   don't think we should accept code like this adding \"unsigned\" to a typedef'd type."

So the project's stated desired behaviour is **a clean diagnostic**, not acceptance.

## "This reproduces" means

**dxc fails internally — crash-shaped — while compiling a translation unit that declares
`unsigned int16_t` (or `unsigned int32_t` / `unsigned int64_t`) at global scope.**

Concretely, any of:

* access violation (`0xC0000005`), which is the exact status the reporter's quoted message
  (`Internal compiler error: access violation. Attempted to read from address 0x...0008`)
  corresponds to;
* an assert firing in an assert-enabled Debug build (`0x80000003` / `0xE0000001`) — the same
  defect wearing its Debug face;
* any other internal-failure status (`0x80AA001B`–`0x80AA001D`, `0xE0000002`/`3`,
  `llvm::cast<X>()` text at E_FAIL).

The predicate must therefore be `internal_failure`, not a text match: the reporter quotes a
Release-build message, ground truth here is a Debug build, and the two need not agree. The
title says "Segfault", which is exactly the symptom most likely to change *shape* between
builds rather than disappear.

**This does NOT reproduce** if dxc emits an ordinary diagnosed error (E_FAIL 0x80004005 with an
`error:` line and no crash), or compiles the shader successfully. Note that a nonzero exit is
*not* by itself a reproduction: dxc returns E_FAIL for ordinary syntax errors.

If the compiler now emits a clean `error:` for `unsigned int16_t`, that is `does-not-repro` for
the crash *and* matches the maintainer's stated desired behaviour — but I must check that the
error is about this construct and not about something incidental in my reconstruction (missing
`-enable-16bit-types`, unknown profile, etc.).

## Claims in the report that are separately checkable

The title and body do not agree about scope of the claim, and both parts are load-bearing.
Each of these is a separate measurement, not an assumption:

| # | claim | source | how I will test it |
| --- | --- | --- | --- |
| A | `unsigned int16_t` at global scope crashes | body | primary repro |
| B | `unsigned int32_t` at global scope crashes | **title only** | variant |
| C | `unsigned int64_t` at global scope crashes | **title only** | variant |
| D | "at global scope" is load-bearing | title | local-scope variant, same type |
| E | qualifiers (`static`, `extern`) don't change it | body | qualified variants |
| F | `uint16_t1x1` (vector/matrix expansion) does **not** crash | body | control, expect no-match |
| G | plain `uint16_t` (the supported spelling) is fine | pow2clk | control, expect no-match |

The title enumerates three types; the body demonstrates one. Titles in this backlog have been
wrong before, so B and C are hypotheses to measure, not facts to inherit.

## Configuration variable I must isolate

`int16_t`/`uint16_t` are 16-bit types and DXC gates them behind **`-enable-16bit-types`**
(shader model 6.2+). So the 16-bit case has two configurations and they may behave differently:

* without `-enable-16bit-types`: the compiler may reject the type before ever reaching the code
  that crashes — that would be an `invalid-probe`-shaped result, not a clean one;
* with `-enable-16bit-types`: the type exists.

`int32_t`/`int64_t` need no such flag, so if B/C reproduce they give a flag-independent repro
and a much longer release history (no SM6.2 floor). I will target the repro at the oldest
profile and flag set that still shows the symptom.

No profile, entry point or command line is given anywhere in the issue, so the command is
reconstructed. A global variable declaration needs no entry point body to be parsed, but dxc
requires an entry point, so the repro will carry a trivial one.

## Repro quality

**partial** — the failing construct is quoted verbatim and is a single line, but the target
profile, entry point, shader model and command line are all absent and must be reconstructed,
and the 16-bit flag question above is not answered by the report.

## History question

Filed 2022-09-14. Expect `always-repro'd` if this is an old front-end defect, but the maintainer
comments (2023, 2024) both describe it as still-live, and llvm-beanz hit it again in Nov 2023.
The 16-bit repro cannot be probed before shader model 6.2 support exists; the 32/64-bit repro,
if it reproduces, should be probeable back to the v1.4.1907 floor. Prereleases are excluded —
the issue names none.

## Anti-rationalisation notes to myself

* Do not read "the compiler printed an error" as "fixed" without checking *which* error: an
  error about `-enable-16bit-types`, an unknown profile or an unknown identifier means the probe
  never reached the code under test.
* Do not read a single build's signature as the whole answer. If Debug ground truth and the
  release binaries disagree in *shape* (assert vs access violation), that is one defect with two
  signatures and wants `any_of`, not a fix.
* Every predicate gets a control that must **not** match.
