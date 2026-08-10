# #4351 — expected symptom

Written **before** running any compiler, from the issue text alone
(<https://github.com/microsoft/DirectXShaderCompiler/issues/4351>), so that
"does not reproduce" stays falsifiable.

Filed 2022-03-25 by `tomjohnstone`, label `bug`, milestone `Dormant`, state
`OPEN`. One comment (2022-08-15, `sparkkk`).

## What the reporter says

Title: *Rewriter incorrectly removes types that are used in a member array of
another struct.*

Body, verbatim in substance: "In the following example `MultipleChildren` being
an array causes `Child` type to be stripped by the rewriter when using
`-remove-unused-globals`", followed by a complete shader and the exact command
line embedded as a comment on its first line:

```
// dxr -E InitArgs -remove-unused-globals test.hlsl
struct Child {
	uint Test;
};

struct Parent {
	Child MultipleChildren[2];
};

RWStructuredBuffer<Parent> ParentBuffer;

[numthreads(1, 1, 1)]
void InitArgs()
{
	ParentBuffer[0] = (Parent)0;
}
```

## Asks, decomposed

The issue carries two distinct claims. They are scored separately.

**Ask 1 (the body, the title, and the only thing with a repro).** `dxr -E
InitArgs -remove-unused-globals` on that source emits rewritten HLSL in which
the `struct Child` *definition is missing*, while `struct Parent` still declares
a member of type `Child`. The output is therefore self-inconsistent: it names a
type it does not define. Two things are implied by "incorrectly" and by the
title's contrast with the non-array case, and both are checkable:

- *`Child` is used*, so removing it is wrong regardless of what else happens —
  the rewriter's own output still references it.
- *the array is the trigger*: a plain `Child SingleChild;` member is expected
  **not** to lose its definition. If both forms lose it, the title is wrong
  about the cause and that is a finding in its own right.

**Ask 2 (the 2022-08-15 comment by `sparkkk`).** "not only for struct members,
but the types of unused function parameters would also be removed incorrectly."
No repro, no command line, no shader — `prose-only`. It is scored as a separate
predicate against a best-effort agent-constructed shader and never folded into
ask 1's verdict.

## Repro quality

`complete` for ask 1: the shader is whole, self-contained, needs no headers, and
the command line is given verbatim including the entry point. `prose-only` for
ask 2. Overall recorded as `complete`, because the issue's headline claim has a
complete repro; ask 2's weakness is stated explicitly rather than averaged in.

## "This reproduces" means, precisely

Running the reporter's command against the reporter's source:

1. the run **succeeds** and emits rewritten HLSL (anti-vacuity — a rewriter that
   errored out, or one that was never reached, has measured nothing and must not
   score as a reproduction just because a definition is absent from an error
   message);
2. the emitted text still contains `struct Parent` with a member declared
   `Child MultipleChildren[2]` (the reference that makes the removal incorrect);
3. the emitted text still contains the entry point `InitArgs`;
4. the emitted text contains **no** `struct Child { ... }` definition.

Clause 4 alone is the symptom; clauses 1–3 exist because clause 4 is an
**absence** and absences are satisfied for free by any run that produced no
output. This is the documented trap (SKILL.md: "An absence-based predicate is
satisfied for free by a compile that never got started"), and it is especially
live here because the rewriter driver's failure mode on old releases is an
HRESULT with no text at all.

## "This does not reproduce" means

The run succeeds and the emitted text contains a `struct Child` definition —
i.e. clauses 1–3 hold and clause 4 fails.

## Controls that must be run, and what each rules out

| control | expectation | what a violation would mean |
| --- | --- | --- |
| non-array member (`Child SingleChild;`), same flags | `no-match` | the title's "member array" cause is wrong; the predicate is not specific to the array form |
| `-remove-unused-globals` **removed** from the command | compare byte-for-byte against the primary run | if identical, the flag is not load-bearing and the issue's attribution to it is wrong |
| `-remove-unused-globals` **misspelled** | must fail loudly | proves the parser actually knows that option name — a clean exit proves nothing, since `/`-prefixed unknown options are silently ignored |
| compile the rewriter's own output with `dxc` | must fail on the undefined type | converts "a definition is missing from some text" into "the produced source is not valid HLSL", which is the actual harm |

## History

The instrument is `dxr.exe`, not `dxc.exe`, so `triage.py bisect` is unavailable
by design. History, if measured, must hold a fixed `dxr.exe` beside each
release's `dxcompiler.dll` and needs per-release probes that can distinguish
"this release rewrote it correctly" from "this release cannot express the
option", plus an equivalence control proving the staging drives the release's
rewriter and not the ground-truth one.

## Prediction recorded for falsifiability

Before measuring: I expect ask 1 to still reproduce on `main`, because the
issue is open, dormant and four years old with no linked PR in its timeline
(events: one `labeled`, one `commented`, one project add, one milestone). That
expectation has no evidentiary weight; it is written down so that agreeing with
it cannot be mistaken for having tested it.
