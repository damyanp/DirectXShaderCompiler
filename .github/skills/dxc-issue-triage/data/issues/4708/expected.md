# 4708 — "Free operator overload" — expected symptom, written before anything was run

Issue: https://github.com/microsoft/DirectXShaderCompiler/issues/4708
Filed 2022-10-06 by @fknfilewalker. Label at fetch time: `hlsl-next`.

## What the issue actually asks

The body is a question, not a defect report:

> If you want to allow "class + x" and "x + class" you need to have free operator
> overloading, is this possible or is there another way around it? If not, could this be a
> future feature?

It attaches a complete compute shader that declares a `template<typename T, uint32_t N>
class array` with a **member** `operator[]`, and then two **non-member** (free, namespace
scope) `operator+` function templates, and uses `arr1 + 2.0f` from `main`.

The one comment, from @llvm-beanz (COLLABORATOR, 2023-06-30), answers the question
directly: the capability is tracked as hlsl-specs proposal *0008 Non-member Operator
Overloading* and "is almost certainly going to make the cut" for HLSL 202x.

## Classification decided BEFORE measuring: enhancement, not defect

This is a **feature request for a language capability HLSL does not have**, not a
regression or a malfunction. Both the reporter ("could this be a future feature?") and the
maintainer (a spec proposal, plus the `hlsl-next` label — *"Bugs for consideration on next
language version"*) treat it that way.

Consequences, fixed now so that the measurement cannot be rationalised afterwards:

- The expected `suggested_action` is **`enhancement-not-bug`**.
- The expected `history` taxonomy value is **`never-implemented`**, *not* `always-repro'd`.
  A capability that was never specified, never implemented and is being designed in the
  spec repo is not "a bug that reproduced in every release". Precedent for this pairing in
  this workspace: issue 4501.
- `status` is still expected to be `repros` in the narrow sense that the reporter's shader
  is still rejected today — but that word must not leak into the write-up as "the bug is
  still there".
- If, contrary to expectation, some DXC release *did* accept a non-member operator
  overload and a later one stopped, that would flip this to a genuine regression and the
  verdict would have to change. That is the one measurement that could overturn the
  classification above, so the history scan is still worth running.

## What "this reproduces" means

**Reproduces** = DXC rejects the reporter's shader *because of the namespace-scope
`operator+` declarations*, i.e. the free operator overload is not a usable HLSL construct.

**Does not reproduce** = the shader compiles, `arr1 + 2.0f` resolves to the free
`operator+`, and DXIL is produced.

The exact diagnostic text is unknown at the time of writing; it will be recorded verbatim
from ground truth and written into `match.json` rather than approximated (SKILL.md's rule
for diagnostic-symptom issues).

## The hazard this issue carries, and the controls that answer it

The symptom **is a diagnostic**. That breaks the `invalid-probe` machinery in exactly the
way SKILL.md warns about: an old release that predates HLSL 2021 templates, or member
operator overloading, or `-HV 2021` itself, will also emit an error, and will therefore
score as a *perfect reproduction* of "the compiler rejects this". A never-implemented
feature is then indistinguishable from an always-broken one, and a bare
`bisect` result would say `always-repro'd` for a reason that has nothing to do with the
issue.

So no release probe counts unless that same release is independently shown to have the
**surrounding capability**. The controls, declared before running:

| file | expectation | what it proves |
| --- | --- | --- |
| `control-member-operator.hlsl` | `--expect no-match` | member operator overloading + class templates work here; `arr + 2.0f` via a *member* `operator+` compiles. This is the per-release feature-presence control: a release that fails this is **unmeasurable**, not a reproduction |
| `control-free-function.hlsl` | `--expect no-match` | a namespace-scope *ordinary* function template (`add(arr, x)`) compiles, so the rejection is specific to `operator`, not to free templates |
| `control-hello.hlsl` | `--expect no-match` | trivial `cs_6_0` shader: the toolchain/profile/flags are usable at all on this build |

`control-member-operator.hlsl` is the one that matters. It is both a negative control for
the predicate (a valid shader the predicate must not fire on) and the per-release positive
control for the capability, and it must be run on **every** release probed, not only on
ground truth.

## Command

`-T cs_6_0 -E main -HV 2021 repro.hlsl`

`cs_6_0` is the oldest profile that can express the repro (the shader is `[numthreads]`).
`-HV 2021` is pinned deliberately: templates and operator overloading are HLSL 2021
features, today's default is already 2021, and pinning makes a release that cannot express
the language mode announce itself (`Unknown HLSL version: 2021`, a recognised
`invalid-probe`) instead of failing for an unrelated reason.

## Repro quality

`complete` — the issue body carries a self-contained shader with a `[numthreads]` entry
point. Only the command line is inferred, and it is the obvious one.

## What would make this triage wrong

- Reporting `always-repro'd`. See above: that framing turns "HLSL never had this" into
  "DXC has been broken since 2019".
- Accepting an old release's error as a reproduction without its capability control.
- Treating a nonzero exit as a crash. DXC returns E_FAIL (0x80004005) for ordinary
  diagnosed errors, and every probe here is expected to be an ordinary diagnosed error.
- Believing a Clang pane that errors, without first proving with a trivial control under
  the same flags that the difference is not just Clang's incomplete HLSL support.

## The question worth answering beyond "does it still repro"

Because this is a language-design request that is already in the spec pipeline, the most
useful thing for a maintainer is **what the successor compiler does**. Compiler Explorer
carries `hlsl_clang_trunk`. If Clang's HLSL front end already accepts a non-member
operator overload, the design question is answered in the successor and this issue's
status changes from "wanted" to "already true over there". That is planned as a first-class
part of the evidence, not an afterthought.
