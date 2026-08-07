# #2604 — Handle `-Fc` in Compile API

*Written before any compiler or harness was run. Recorded to keep "does not
reproduce" falsifiable (SKILL.md step 2).*

Issue: <https://github.com/microsoft/DirectXShaderCompiler/issues/2604>
Filed 2019-11-26. Label: `enhancement`. 2 comments.

## What the issue says

The body is a single sentence:

> Handle -Fc in Compile API in order to support separate simultaneous
> disassembly output.

Two comments add the only other facts on record:

1. **2020-07-30, a non-member reporter** — *"Is this still not resolved in
   latest version of dxc (it looks like it isn't)? Could anyone update
   documentation which option works or not when using compile api? I lost alot
   of time trying to figure out why -Fc works in stand alone dxc, but not from
   compile api (**E_INVALIDARG was returned**). Documentation states that all
   options are recognized by library calls: …/docs/SPIR-V.rst"*
2. **2024-06-20, @damyanp (MEMBER)** — *"Moved to Dormant - we'd happily review
   a PR that adds support for this, but we're not planning on adding it to
   DXC."*

So there are **two distinct claims**, and they are not the same claim:

| | claim | source |
| --- | --- | --- |
| **A** | The Compile API **rejects** `-Fc` — `Compile` returns `E_INVALIDARG` | 2020 comment |
| **B** | The Compile API does not **honour** `-Fc`, i.e. there is no way to get disassembly out of a single `Compile` call alongside the object | issue body |

A is a bug-shaped observation about argument parsing. B is the enhancement
actually being requested: *"separate simultaneous disassembly output"* — one
call producing both the container and its disassembly. A could be fixed
(argument accepted) while B remains unimplemented (argument accepted and then
ignored), and that combination would be the worst outcome for a caller, because
it is silent.

Note also that this issue predates `IDxcCompiler3` (added in DXC 1.6, 2020). In
2019 "the Compile API" meant `IDxcCompiler::Compile` /
`IDxcCompiler2::CompileWithDebugInfo`. `IDxcCompiler3::Compile` returns an
`IDxcResult` that has a **`DXC_OUT_DISASSEMBLY`** output kind, so the modern API
has somewhere to put the answer that the 2019 API did not. Whether `Compile`
ever fills it is exactly the thing to measure.

## What "this reproduces" means

**Reproduces** if, on the ground-truth build, passing `-Fc` to the *compile*
entry points still fails to give the caller a disassembly, in either of these
two ways:

* `Compile` returns a failing `HRESULT` (specifically `E_INVALIDARG`,
  `0x80070057`) or a failing result status carrying an unknown/unsupported
  argument diagnostic; **or**
* `Compile` succeeds but no disassembly is produced anywhere the caller can
  reach it — no `DXC_OUT_DISASSEMBLY` on the `IDxcResult`, and no file written
  at the path `-Fc` named.

**Does not reproduce** only if a single `Compile` call with `-Fc` yields the
disassembly text to the caller — either as `DXC_OUT_DISASSEMBLY` on the result,
or as the named file on disk — *and* the object code is still produced. That is
what "separate simultaneous disassembly output" asks for.

**Changed behavior** if the 2020 comment's `E_INVALIDARG` is gone but the
disassembly still is not produced: the argument is now accepted and silently
does nothing. That is a real and reportable change of shape (the caller's error
handling no longer fires), and it is the outcome I would bet on for a six-year
window, so I am writing it down before measuring rather than after.

**Not-compiler-verifiable does not apply.** This is entirely a compiler/API
question; nothing needs a GPU or a runtime.

## Controls this needs

The symptom is partly an **absence** (no disassembly reaches the caller), and
SKILL.md is emphatic that absence clauses are satisfied for free by a call that
never ran. So:

* a **baseline** case with no `-Fc` at all, proving the harness compiles the
  shader successfully and that whatever output kinds do exist are enumerated —
  if the baseline also shows "no disassembly", the absence clause is measuring
  the harness, not the compiler;
* a **positive** case proving disassembly *is* obtainable from the same DLL by
  the supported route (`IDxcCompiler3::Disassemble` / `IDxcCompiler::Disassemble`
  on the compiled object). This is the "the feature exists, it is just not
  reachable from `Compile`" anchor, and without it "no disassembly" could just
  mean the harness cannot find disassembly at all;
* a **known-accepted-flag** case (a flag the compile API definitely does honour)
  to show that the rejection, if any, is specific to `-Fc` and not to the way
  the harness passes arguments;
* the same probes through **`dxc.exe`**, where `-Fc` is documented to work, to
  confirm the command-line/API split the issue is actually about.

## Repro quality

`agent-constructed`. The issue supplies no code at all — one sentence in the
body, and a prose report of `E_INVALIDARG` in a comment with no snippet. A C++
harness against `dxcompiler.dll` has to be written to ask the question, so any
conclusion is about the harness's reading of the API as much as about the
compiler, and the harness has to be committed and runnable for the verdict to
mean anything.

## Predicted history

`always-repro'd` seems most likely for claim B — the 2024 maintainer comment
says outright that it is not planned — but claim A's `E_INVALIDARG` is exactly
the sort of thing that could have been quietly changed by an unrelated
options-table edit, so the two need separate treatment and possibly separate
predicates.

## Suggested action if it reproduces

Likely `enhancement-not-bug` — the label is already `enhancement` and a
maintainer has stated a position — but the *useful* finding would be about the
2020 comment: whether the documentation claim it complains about is still
wrong, and whether the error a caller gets today is any more discoverable than
it was. If `E_INVALIDARG` has silently become "accepted and ignored", that is
worth saying regardless of whether anyone implements the feature.
