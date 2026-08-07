# #2188 — expected symptom

Written **before** anything was compiled, from the issue text and its one comment.

## What the issue says

Filed 2019-05-14 by an external reporter, labelled `bug` + `fxc-disagrees`, milestone
`Dormant`. Body (verbatim structure):

```hlsl
static const uint2	c2Thread= uint2(8, 8);
static const uint       cThread = c2Thread.x*c2Thread.y;
groupshared float4      S1[cThread];
[numthreads(c2Thread.x, c2Thread.y, 1)]
void csMain() ....
```

> This code construct used to work with fxc.exe but doesn't compile with dxc. Is this
> expected?

and a "note" from the reporter that **inlining the numerical constants does work fine**:

```hlsl
groupshared float4      S1[64];
[numthreads(8, 8, 1)]
```

The single comment, from @tristanlabelle (2019-05-16, DXC contributor):

> Thanks for reporting! I was able to repro. If this blocking, you can use a `#define`
> as a workaround.

So a DXC contributor confirmed the repro in 2019 and offered a preprocessor workaround.
Nobody has stated a diagnosis, and nobody has quoted the diagnostic — the issue never
says *how* it fails, only that it does not compile.

## "This reproduces" means

**The shader below fails to compile with a nonzero exit status, while the reporter's
inlined-constant version of the same shader compiles cleanly.**

Both halves are needed. "dxc exits nonzero" on its own is not the symptom — the issue is
a *disagreement*: a construct FXC accepts is rejected here, and the reporter's own
control (numeric literals inlined) is the thing that must still work for the failure to
be about `static const` constant-folding rather than about something else in the shader.

Deliberately **not** pinned in advance:

- **the diagnostic text.** The issue does not quote one, so requiring a particular
  message would be inventing a symptom the report does not contain.
- **whether the failure is a clean diagnostic or an internal failure.** Cross-referenced
  #2191 ("Assert when a static const uint is used with `[numthreads]`", still open) says
  the closely-related scalar case *asserts*. This ground truth is a Debug build, so an
  assert is a live possibility here, and it would still be "doesn't compile". A
  predicate that demanded `error:` text would score an assert as "fixed"; one that
  demanded an assert would score a clean diagnostic as "fixed". Either is the same
  wrong-verdict trap in two directions.
- **which of the two constructs fails.** The reported shader uses the `static const` in
  two places at once — the `groupshared` array bound and the `[numthreads]` arguments —
  and the reporter changed both at once in the working version. Which one (or both) is
  responsible is a triage finding, not an input.

## Not the symptom

- A warning. Warnings do not stop a compile.
- A validation failure or wrong codegen. The report is about the compile being rejected;
  it never gets as far as produced code.
- A failure of the *inlined* version. If that also fails, the repro is wrong (the elided
  `void csMain() ....` body would be the suspect), not the compiler.

## Repro quality

**`partial`.** The reporter gave the exact declarations that matter, but the entry point
body is elided as `....`, so a compilable file has to be completed during triage. The
completion must not itself be able to cause the failure — hence the inlined-constant
control, which is the reporter's own, run over the *same* completed body.

## What would make this `does-not-repro`

The completed shader compiles to DXIL with exit 0 on `main-debug`, and the control also
compiles to exit 0. Anything else — including a different failure mode from the one the
2019 thread implies — is `repros` or `changed-behavior`, and needs the two constructs
separated before it can be called.

## FXC's side

The `fxc-disagrees` label asserts FXC accepts this. That is a claim about a compiler this
skill does not build, so it must be *shown*, not repeated: either a local `fxc.exe` from
the Windows SDK captured as a `manual-case-*` file, or a Compiler Explorer pane using
`fxc_10_0_19041`, or both. If neither is available, the label's claim stays attributed to
the reporter rather than verified here.
