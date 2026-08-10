# #3883 — what "this reproduces" means

Written **before** running any compiler.

## The report

[#3883](https://github.com/microsoft/DirectXShaderCompiler/issues/3883) "DXC Compiler Crash",
filed 2021-07-16 by @Tom-Lopes. Labels: `bug`, `crash`, `incorrect-code`. The whole body is a
minimal shader plus one sentence:

> This minimal repro code snippet will **crash DXC rather than emitting an error message**:

```hlsl
cbuffer cb0 : register(b0)
{
    float4 colors[4];
}

float4 PSMain() : SV_TARGET
{
    uint index = index; // Initializing a variable to itself is bad!
    return colors[index];
}
```

The construct under test is a **self-initialising local**: `uint index = index;`, where the
initialiser names the variable being declared. That is legal to *parse* in C++ (the name is in
scope from its own declarator) and reads an uninitialised value. The reporter's position is
that this is bad input which should be diagnosed, and that dxc instead dies.

Note what `incorrect-code`'s label description actually says here: *"Issues relating to
handling of incorrect code"* — i.e. how dxc handles **erroneous input**, not "dxc emits
incorrect code". So the two labels together read as "dxc crashes on bad input instead of
diagnosing it", which is exactly the body's sentence.

## Prior datapoints in the thread

| when | who | claim |
| --- | --- | --- |
| 2024-07-23 | @damyanp (MEMBER) | "The crash still repros, although the compiler does emit a warning pointing to the bad code", with `https://godbolt.org/z/j8GbsYToe` |

Read back through `GET /api/shortlinkinfo/j8GbsYToe`, that link holds the issue's shader
verbatim and one pane: `dxc_trunk` with options `-T ps_6_6 -E PSMain`. So the maintainer's
2024 check used **ps_6_6**, and it establishes two things to test against:

1. the crash was still live in 2024 on a CE (Release) build; and
2. a **warning** is emitted that the 2021 body does not mention — the body's "rather than
   emitting an error message" was already partly out of date by 2024. If ground truth now
   warns, that is not by itself a change of verdict.

## Repro configuration

The body never names a target profile. `PSMain()` returns `float4 : SV_TARGET`, so it is a
pixel shader, and the entry point is spelled out. I will run:

```
-T ps_6_0 -E PSMain repro.hlsl
```

**ps_6_0, deliberately not the maintainer's ps_6_6.** The shader uses nothing newer than SM
6.0, and a repro targeting ps_6_6 would be rejected outright by every release older than
v1.6.2104-ish (`error: invalid profile ps_6_6`), scoring those as clean and faking a fix
boundary. Per SKILL.md, target the oldest profile that still shows the symptom. I will run the
maintainer's exact `-T ps_6_6` line as a **labelled variant** so the two are comparable and
the reporter's/maintainer's configuration is on record.

No workaround flags were used by the reporter, so there are none to question.

## Reproduces if

**dxc fails internally on the repro.** The predicate must be `internal_failure`
(exit-status-based), never a match on assert or crash text:

- the Debug ground truth is expected to trap an assert (`0x80000003`) or throw one
  (`0xE0000001`), while release binaries would access-violate (`0xC0000005`) or surface a
  `cast<X>()` type mismatch as plain `E_FAIL` — the same defect, three different texts;
- an internal failure can print **nothing at all** on older releases (#3259), so a text marker
  would score a real crash as clean;
- the Windows build prints `llvm::cast<X>()` where CE's Linux build prints bare `cast<X>()`.

## Does **not** reproduce if

- dxc exits 0 and emits DXIL (with or without a warning), **or**
- dxc rejects the shader with an ordinary **diagnosed** error: `E_FAIL` (0x80004005) plus an
  `error:` line. That is the shape a *fix* for this issue would take — "emit an error message
  rather than crash" is literally what the reporter asked for. It exits nonzero and it is
  **not** an internal failure; treating "nonzero exit" as "crash" here would report the fix as
  the bug.

## The outcome I must not collapse

The issue is `crash` **and** about handling of incorrect code, so there is a third possibility
between "still crashes" and "fixed":

> dxc no longer crashes, but still **silently accepts** the self-initialising declaration and
> emits DXIL that indexes the constant buffer with an undefined value.

That is `changed-behavior`, not `does-not-repro`, and it is the more valuable finding, because
anyone spot-checking the 2021 title against a clean exit would wrongly write "cannot
reproduce". If ground truth does not crash, I will write a **second predicate**
(`match-accepted.json`) anchored on a positive artifact only successful codegen can emit — an
`undef` reaching the CBuffer index computation — and bisect it separately from the crash
predicate, so the two histories sit side by side.

Conversely, if ground truth crashes *and* warns, the crash predicate is the verdict and the
warning is a note.

## Controls planned

- `control-initialised.hlsl` — the identical shader with `uint index = 0;`. Known-good input;
  the predicate must **not** fire (`--expect no-match`). Without it, "the predicate matched"
  is indistinguishable from "the predicate matches everything".
- If a second, absence/text-based predicate is needed for the changed-behaviour branch, it
  gets its own control on the same shader.

## Repro quality

`complete` — the body carries a self-contained shader and names the entry point; the stage is
unambiguous from `SV_TARGET` and the profile is corroborated by the maintainer's CE link. The
only thing I supply is the shader-model number, and that choice is recorded above.
